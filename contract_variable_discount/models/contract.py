# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


def _format_discount(value):
    if isinstance(value, str):
        return value
    return "%.2f %%" % value


def _format_amount(value):
    if isinstance(value, str):
        return value
    return "%.2f €" % value


class ContractTemplateLine(models.Model):
    _inherit = "contract.template.line"

    discount_line_ids = fields.One2many(
        string="Variable discount lines",
        comodel_name="contract.template.discount.line",
        inverse_name="contract_template_line_id",
        cascade="delete",
        copy=True,
    )

    variable_discount = fields.Boolean(
        "Variable discount?", store=False, compute="_compute_variable_discount"
    )

    @api.depends("discount_line_ids")
    def _compute_variable_discount(self):
        for record in self:
            record.variable_discount = bool(record.discount_line_ids)


class ContractLine(models.Model):
    _inherit = "contract.line"

    contract_template_line_id = fields.Many2one(
        string="Contract template line",
        help="Contract template line which discount lines apply here",
        comodel_name="contract.template.line",
        domain=lambda self: self._domain_contract_template_line_id(),
    )

    inherited_discount_line_ids = fields.One2many(
        string="Inherited discount lines",
        help="Discount lines from the related contract model",
        related="contract_template_line_id.discount_line_ids",
        readonly=True,
    )

    specific_discount_line_ids = fields.One2many(
        string="Specific discount lines",
        help="These lines complete the contract template's, if any",
        comodel_name="contract.discount.line",
        inverse_name="contract_line_id",
        copy=True,
    )

    variable_discount = fields.Boolean(
        "Variable discount?", store=False, compute="_compute_variable_discount"
    )

    def _domain_contract_template_line_id(self):
        contract = self.contract_id
        if not contract and "contract_id" in self.env.context:
            contract = contract.browse(self.env.context["contract_id"])
        return [("contract_id", "=", contract.contract_template_id.id)]

    @api.model
    def _prepare_invoice_line(self, invoice_id=False, invoice_values=False):
        "Compute discount and append discount description to invoice line name"
        vals = super(ContractLine, self)._prepare_invoice_line(
            invoice_id, invoice_values
        )

        result = self.compute_discount(invoice_values["date_invoice"])

        vals["discount"] = result["total"]
        descriptions = result["descriptions"]
        if descriptions:
            vals["name"] += "\n" + (
                _("Applied discounts:\n- %s") % "\n- ".join(descriptions)
            )

        return vals

    @api.depends(
        "contract_template_line_id.discount_line_ids", "specific_discount_line_ids"
    )
    def _compute_variable_discount(self):
        for record in self:
            record.variable_discount = bool(
                record.specific_discount_line_ids
                or record.contract_template_line_id.discount_line_ids
            )

    @api.multi
    def compute_discount(self, date_invoice):
        """Compute the discount of current contract line for given invoice date

        Returns a dict like:
        - total: the total computed amount
        - descriptions: a list of strings describing the discounts

        A contract line specific discount line may replace a discount
        of its related contract template line using the
        replace_discount_line_id relation.

        0-valued discounts are ignored, so to remove a contract
        template's discount, one can replace it with a 0-valued
        contract line discount.
        """

        total_discount = 0.0
        customer_descriptions = []

        for discount_line in self._applicable_discount_lines():
            value = discount_line.compute(self, date_invoice)
            if value is not None and value > 0.0:
                total_discount += value
                customer_descriptions.append(discount_line.name)

        return {
            "total": total_discount,
            "descriptions": customer_descriptions,
        }

    def _applicable_discount_lines(self):
        """Yields applicable discount lines, either contract.discount.line or
        contract.template.discount.line instances.
        """
        self.ensure_one()

        c_lines = self.specific_discount_line_ids
        replaced_ids = c_lines.mapped("replace_discount_line_id").ids

        for line in self.contract_template_line_id.discount_line_ids:
            if line.id not in replaced_ids:
                yield line

        for line in c_lines:
            yield line


class Contract(models.Model):
    _inherit = "contract.contract"
    discount_date_units = {"days", "weeks", "months", "years"}

    @api.multi
    def _convert_contract_lines(self, contract):
        """On each contract line, add the relation to the contract template
        line which generated it.

        This makes it easy to find the application contract template
        discount lines.
        """
        new_lines = super(Contract, self)._convert_contract_lines(contract)
        for contract_line, contract_template_line in zip(
            new_lines, contract.contract_line_ids
        ):
            contract_line.contract_template_line_id = contract_template_line
        return new_lines
