import logging
from collections import defaultdict
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__file__)

CONTRACT_PROD_MARKER = "##PRODUCT##"
CONTRACT_ACCESSORY_MARKER = "##ACCESSORY##"
NO_DATE = date(2030, 1, 1)


def _rental_products(contract_descr):
    "Helper function to prepare data required for contract line generation"
    so_line = contract_descr["so_line"]

    _acs = defaultdict(int)
    for items in contract_descr["accessories"]:
        _acs[items] += 1
    __acs = [(p, l, q) for ((p, l), q) in _acs.items()]

    return {
        CONTRACT_PROD_MARKER: [(so_line.product_id, so_line, 1)],
        CONTRACT_ACCESSORY_MARKER: sorted(__acs, key=lambda a: a[0].id),
    }


class ContractLine(models.Model):
    _inherit = "contract.line"

    contract_template_line_id = fields.Many2one(
        string="Contract template line",
        help="Contract template line which generated current contract line",
        comodel_name="contract.template.line",
        domain=lambda self: self._domain_contract_template_line_id(),
    )

    def _domain_contract_template_line_id(self):
        contract = self.contract_id
        if not contract and "contract_id" in self.env.context:
            contract = contract.browse(self.env.context["contract_id"])
        return [("contract_id", "=", contract.contract_template_id.id)]


class Contract(models.Model):
    _inherit = "contract.contract"

    contractual_documents = fields.Many2many(
        string="Contractual documents",
        comodel_name="ir.attachment",
        domain=[("public", "=", True), ("res_model", "=", False)],
    )

    commitment_period_number = fields.Integer(
        string="Commitment period number",
        help="Commitment duration in number of periods",
        default=0,
        required=True,
    )

    commitment_period_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("monthlylastday", "Month(s) last day"),
            ("quarterly", "Quarter(s)"),
            ("semesterly", "Semester(s)"),
            ("yearly", "Year(s)"),
        ],
        default="monthly",
        string="Commitment period type",
        required=True,
    )

    commitment_end_date = fields.Date(
        string="Commitment end date",
        compute="_compute_commitment_end_date",
        store=True,
    )

    date_start = fields.Date(inverse="_inverse_date_start")

    recurring_next_date = fields.Date(inverse="_inverse_recurring_next_date")

    @api.multi
    def _convert_contract_lines(self, contract):
        """On each contract line, add the relation to the contract template
        line which generated it.
        """

        new_lines = super(Contract, self)._convert_contract_lines(contract)
        for contract_line, contract_template_line in zip(
            new_lines, contract.contract_line_ids
        ):
            contract_line.contract_template_line_id = contract_template_line
        return new_lines

    def _inverse_date_start(self):
        "Allow the direct modification of the start date"
        for record in self:
            for cline in record.contract_line_ids:
                cline.date_start = record.date_start
                cline._onchange_date_start()

    def _inverse_recurring_next_date(self):
        """Allow the direct modification of the next recurring date

        ... if no invoice with a date later than the new next date exists
        (even draft one may be aggregated and invoiced, so we really need
         no invoice past that date).

        In that case, set the next date and reset the last_date_invoiced
        of each line.

        """
        force = self._context.get("force_recurring_next_date", False)

        for record in self:
            new_date = record.recurring_next_date
            active_invlines = self.env["account.invoice.line"].search_count(
                [
                    ("contract_line_id", "in", record.contract_line_ids.ids),
                    ("invoice_id.date_invoice", ">=", new_date),
                    ("invoice_id.state", "!=", "cancel"),
                ]
            )
            if not force and active_invlines:
                raise ValidationError(
                    "There are invoices past the new next recurring date."
                    " Please remove them before."
                )

            inv_dates = (
                record._get_related_invoices()
                .filtered(lambda inv: inv.state != "cancel")
                .mapped("date_invoice")
            )
            last_date_invoiced = inv_dates and max(inv_dates) or False

            if force and last_date_invoiced and last_date_invoiced >= new_date:
                real_last_date_invoiced = last_date_invoiced
                last_date_invoiced = max(
                    [d for d in inv_dates if d < new_date] + [record.date_start]
                )
                _logger.warning(
                    "Forcing last_date_invoiced to %s although last invoice"
                    " date is %s",
                    last_date_invoiced,
                    real_last_date_invoiced,
                )

            _logger.info(
                "Setting all contract %s lines last_date_invoiced"
                " to %s and recurring_next_date to %s",
                record.name,
                last_date_invoiced,
                new_date,
            )

            for cline in record.contract_line_ids:
                # Update last_date_invoiced first to avoid model constraint
                cline.last_date_invoiced = last_date_invoiced
                cline.recurring_next_date = new_date

    @api.depends("date_start", "commitment_period_number", "commitment_period_type")
    def _compute_commitment_end_date(self):
        delta = self.env["contract.line"].get_relative_delta
        for record in self:
            if record.date_start:
                record.commitment_end_date = record.date_start + delta(
                    record.commitment_period_type, record.commitment_period_number
                )

    @api.onchange("contract_template_id")
    def _onchange_contract_template_id(self):
        """ """
        if "contractual_documents" not in self.NO_SYNC:
            self.NO_SYNC.append("contractual_documents")

        super()._onchange_contract_template_id()

        docs = self.mapped("contract_template_id.contractual_documents")
        if self.partner_id.lang:
            docs = docs.filtered(lambda d: d.lang in (False, self.partner_id.lang))
        self.update({"contractual_documents": [(6, 0, docs.ids)]})

        contract_descr = self.env.context.get("contract_descr")
        if contract_descr:
            self._modify_from_description(contract_descr)

    def _modify_from_description(self, contract_descr):
        """Implement a commown-specific way to generate the contracts from a sale:

        - more than one contract is generated by sale order line: one per unit of
          contract product (i.e. product that has a property_contract_template_id),
          trying to group the products with their accessories; this more or less complex
          repartition of the sold product is computed in sale.order model's
          `assign_contract_products` method and transmitted through the context for each
          contract in the `contract_descr` parameter.

        - the contract template can have lines marked with ##PRODUCT## or ##ACCESSORY##;
          once the contract lines are generated using the standard contract module
          method (see `_onchange_contract_template_id`), those contract lines will be
          considered themselves as template lines: the ##PRODUCT## marked line will be
          the one for the contract product, the ##ACCESSORY## marked one will generate
          one contract line per accessory. Those templates lines are then removed.

        """
        so_line = contract_descr["so_line"]  # main product so line
        order = so_line.order_id
        aaccount = order.analytic_account_id and order.analytic_account_id

        self.contract_line_ids.update({"recurring_next_date": NO_DATE})
        self.contract_line_ids.update(
            {
                "date_start": NO_DATE,
                "analytic_account_id": aaccount.id,
                "sale_order_line_id": so_line.id,
            }
        )

        rental_products = _rental_products(contract_descr)

        for sequence, line in enumerate(self.contract_line_ids):
            for marker, products in rental_products.items():
                if marker in line.name:
                    for product, so_line, quantity in products:
                        line.copy(
                            {
                                "name": line.name.replace(marker, product.name),
                                "sequence": sequence,
                                "specific_price": so_line.compute_rental_price(
                                    line.product_id.taxes_id
                                ),
                                "quantity": quantity * line.quantity,
                                "sale_order_line_id": so_line.id,
                            }
                        )
                    # Remove marked line once it was used
                    line.cancel()
                    line.unlink()
                    break
            else:
                line.sequence = sequence

        self.contract_line_ids._onchange_date_start()
        self._compute_date_end()

    @api.model
    def of_sale(self, sale):
        return self.search(
            [
                ("contract_line_ids.sale_order_line_id.order_id", "=", sale.id),
            ]
        )

    @api.multi
    def action_show_analytic_lines(self):
        self.ensure_one()
        account = self.mapped("contract_line_ids.analytic_account_id").filtered(
            lambda acc: acc.name == self.name
        )
        if account:
            return {
                "name": _("Cost/Revenue"),
                "type": "ir.actions.act_window",
                "res_model": "account.analytic.line",
                "view_mode": "tree,form,graph,pivot",
                "domain": "[('account_id', '=', %d)]" % account.id,
                "target": "current",
            }
        else:
            return False

    def get_main_rental_line(self, _raise=True):
        """Return the main rental line of current contract.

        This line is:
        1. related to a sold product having a property_contract_template_id
        2. related to a contract template line that is marked with ##PRODUCT##

        Raise if we could not find one (and only one).
        """
        cline_to_property_ct = (
            "sale_order_line_id.product_id.product_tmpl_id"
            ".property_contract_template_id"
        )

        clines = self.env["contract.line"].search(
            [
                ("contract_id", "=", self.id),
                (cline_to_property_ct, "!=", False),
                ("contract_template_line_id.name", "like", CONTRACT_PROD_MARKER),
            ]
        )

        if _raise and len(clines) != 1:
            raise ValidationError(
                _("Contract %s (id %d) has %d main rental service lines.")
                % (self.name, self.id, len(clines))
            )

        return clines

    def get_main_rental_service(self, _raise=True):
        """Return the main rental service of current contract.

        See documentation of `get_main_rental_line` for more details.
        Raise if we could not find one (and only one).
        """

        self.ensure_one()
        clines = self.get_main_rental_line(_raise=_raise)
        services = clines.mapped("sale_order_line_id.product_id.product_tmpl_id")
        if (
            _raise
            and services.property_contract_template_id != self.contract_template_id
        ):
            msg = _(
                "Contract %s (id %d) has a main rental service"
                " with an incoherent contract model %s"
            )
            raise ValidationError(
                msg % (self.name, self.id, services.property_contract_template_id.name)
            )
        return services
