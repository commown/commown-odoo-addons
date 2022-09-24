from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RentalFeesDefinition(models.Model):
    _name = "rental_fees.definition"
    _description = (
        "A definition of fees to be paid back to the supplier when renting his hardware"
    )

    name = fields.Char(required=True, copy=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        help="The supplier concerned by this fees definition",
        required=True,
        domain=[("supplier", "=", True)],
    )

    model_invoice_id = fields.Many2one(
        "account.invoice",
        string="Invoice model",
        help=(
            "Invoice to be used as a model to generate future fees invoices."
            " First line MUST be the fees as their amount will be replaced by"
            " the computed amount."
            " The optional marker ##DATE## in an invoice line description will"
            " be replaced by the fees computation date."
        ),
        domain='[("partner_id", "=", partner_id), ("type", "=", "in_invoice")]',
    )

    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        help="The product concerned by this fees definition",
        required=True,
        domain=[("type", "=", "product")],
    )

    order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="Purchase orders",
    )

    line_ids = fields.One2many(
        comodel_name="rental_fees.definition_line",
        string="Fees definition lines",
        inverse_name="fees_definition_id",
        cascade="delete",
        copy=False,
    )

    computation_ids = fields.One2many(
        comodel_name="rental_fees.computation",
        string="Fees computations",
        inverse_name="fees_definition_id",
        copy=False,
    )

    non_draft_computation_count = fields.Integer(
        default=0,
        compute="_compute_computation_count",
    )

    @api.depends("computation_ids.state")
    def _compute_computation_count(self):
        for record in self:
            record.non_draft_computation_count = len(
                record.computation_ids.filtered(lambda r: r.state != "draft")
            )

    @api.multi
    def write(self, vals):
        "Deny updates when there are already non draft computations"
        for record in self:
            if record.non_draft_computation_count > 0:
                raise ValidationError(
                    _(
                        "Some non-draft computations use this fees definition."
                        " Please remove or set them draft to modify the definition."
                    )
                )
        return super().write(vals)

    @api.constrains("partner_id")
    def _check_partner_coherency(self):
        for fees_def in self:
            if fees_def.mapped("order_ids.partner_id") != self.partner_id:
                raise models.ValidationError(
                    _(
                        "Fees definition purchase orders partners must all be"
                        " the same as the fees definition's partner"
                    )
                )

    @api.constrains("partner_id", "product_template_id", "order_ids")
    def _check_no_po_override(self):
        for fees_def in self:
            overrides = self.env[self._name].search(
                [
                    ("id", "!=", fees_def.id),
                    ("partner_id", "=", fees_def.partner_id.id),
                    ("product_template_id", "=", fees_def.product_template_id.id),
                    ("order_ids", "in", fees_def.order_ids.ids),
                ]
            )
            if overrides:
                raise models.ValidationError(
                    _(
                        "At least one other fees def, %s (id %d), has the same"
                        " partner, product & order"
                    )
                    % (overrides[0].name, overrides[0].id)
                )

    def devices(self):
        return self.mapped("order_ids.picking_ids.move_line_ids.lot_id").filtered(
            lambda d: d.product_id.product_tmpl_id == self.product_template_id
        )

    @api.multi
    def button_open_devices(self):
        self.ensure_one()
        return {
            "name": _("Devices"),
            "domain": [("id", "in", self.devices().ids)],
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "stock.production.lot",
        }


class RentalFeesDefinitionLine(models.Model):
    _name = "rental_fees.definition_line"
    _description = "Define how to compute rental fees value on a period of time"
    _order = "sequence"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
        required=True,
    )

    sequence = fields.Integer(
        string="Index of the period in the fees definition",
        help="Useful to order the periods in the fees definition",
        required=True,
    )

    duration_value = fields.Integer(
        string="Duration value",
        help=(
            "Value of the duration of the period, in duration units."
            " No duration_value means infinite duration."
        ),
    )

    duration_unit = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years"),
        ],
        string="Duration unit",
        help="Units of the duration of the period",
        default="months",
        required=True,
    )

    fees_type = fields.Selection(
        [("fix", "Fixed"), ("proportional", "Proportional")],
        string="Fees type",
        help=(
            "Fixed: value is a monthly time-independent amount. "
            "Proportional: value is the monthly fees for full price"
            " - fees will be computed proportionally with today's price"
        ),
        default="fixed",
        required=True,
    )

    monthly_fees = fields.Float(
        string="Monthly fees",
        help="This value is to be interpreted using fees type",
        required=True,
    )

    @api.multi
    def write(self, vals):
        "Deny updates when there are already non draft computations"
        for record in self:
            if record.fees_definition_id.non_draft_computation_count > 0:
                raise ValidationError(
                    _(
                        "Some non-draft computations use this fees definition."
                        " Please remove or set them draft to modify the definition."
                    )
                )
        return super().write(vals)

    def name_get(self):
        result = []
        for record in self:
            name = record.fees_definition_id.name + " / %d" % record.sequence
            result.append((record.id, name))
        return result

    @api.multi
    def compute_end_date(self, origin_date):
        self.ensure_one()
        if self.duration_value:
            return origin_date + relativedelta(
                **{self.duration_unit: self.duration_value}
            )

    @api.multi
    def compute_fees(self, period):
        """Simplist computation of the fees based on the invoiced amounts in
        the period.

        When contract periodicity is bigger than a month, the fees may
        be 0 for a while then paid in one big go.
        """

        self.ensure_one()

        assert (
            period["to_date"] <= fields.Date.today()
        ), "Future fees computations are not supported yet"

        contract = period["contract"]
        pt = self.fees_definition_id.product_template_id

        invoice_lines = self.env["account.invoice.line"].search(
            [
                ("contract_line_id.contract_id", "=", contract.id),
                ("invoice_id.date_invoice", ">=", period["from_date"]),
                ("invoice_id.date_invoice", "<=", period["to_date"]),
                (
                    "contract_line_id.sale_order_line_id.product_id.product_tmpl_id.storable_product_id",
                    "=",
                    pt.id,
                ),
            ],
        )

        if self.fees_type == "fixed":
            multiplier = 12 if contract.recurring_rule_type == "yearly" else 1
            return self.monthly_fees * multiplier * len(invoice_lines)

        elif self.fees_type == "proportional":
            return (
                sum(i.price_total - i.price_tax for i in invoice_lines)
                * self.monthly_fees
            )
