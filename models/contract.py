# coding: utf-8
# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import uuid

from texttable import Texttable

from odoo import fields, models, api, _
from odoo.exceptions import UserError


def _format_discount(value):
    if isinstance(value, unicode):
        return value
    return u"%.2f %%" % value


def _format_amount(value):
    if isinstance(value, unicode):
        return value
    return u"%.2f €" % value


class ContractTemplateLine(models.Model):
    _inherit = "account.analytic.contract.line"

    discount_line_ids = fields.One2many(
        string=u"Variable discount lines",
        comodel_name="contract.template.discount.line",
        inverse_name="contract_template_line_id",
        cascade="delete",
        copy=True,
    )

    variable_discount = fields.Boolean(
        "Variable discount?", store=False, compute='_compute_variable_discount')

    @api.depends('discount_line_ids')
    def _compute_variable_discount(self):
        for record in self:
            record.variable_discount = bool(record.discount_line_ids)


class ContractLine(models.Model):
    _inherit = "account.analytic.invoice.line"

    contract_template_line_id = fields.Many2one(
        string=u"Contract template line",
        help=u"Contract template line which generated current contract line",
        comodel_name="account.analytic.contract.line",
    )

    inherited_discount_line_ids = fields.One2many(
        string=u"Inherited discount lines",
        help=u"Discount lines from the related contract model",
        related=u"contract_template_line_id.discount_line_ids",
        readonly=True,
    )

    specific_discount_line_ids = fields.One2many(
        string=u"Specific discount lines",
        help=u"These lines complete the contract template's, if any",
        comodel_name="contract.discount.line",
        inverse_name="contract_line_id",
        copy=True,
    )

    variable_discount = fields.Boolean(
        "Variable discount?", store=False, compute='_compute_variable_discount')

    @api.depends('contract_template_line_id.discount_line_ids',
                 'specific_discount_line_ids')
    def _compute_variable_discount(self):
        for record in self:
            record.variable_discount = bool(
                record.specific_discount_line_ids or
                record.contract_template_line_id.discount_line_ids)

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

        total_discount = 0.
        customer_descriptions = []

        for discount_line in self._applicable_discount_lines():
            value = discount_line.compute(self, date_invoice)
            if value is not None and value > 0.:
                total_discount += value
                customer_descriptions.append(discount_line.name)

        return {
            "total": total_discount,
            "descriptions": customer_descriptions,
        }

    def _applicable_discount_lines(self):
        """ Yields applicable discount lines, either contract.discount.line or
        contract.template.discount.line instances.
        """
        self.ensure_one()

        c_lines = self.specific_discount_line_ids
        replaced_ids = c_lines.mapped('replace_discount_line_id').ids

        for line in self.contract_template_line_id.discount_line_ids:
            if line.id not in replaced_ids:
                yield line

        for line in c_lines:
            yield line


class Contract(models.Model):
    _inherit = "account.analytic.account"
    discount_date_units = {"days", "weeks", "months", "years"}

    @api.multi
    def _convert_contract_lines(self, contract):
        """On each contract line, add the relation to the contract template
        line which generated it.

        This makes it easy to find the application contract template
        discount lines.
        """
        new_lines = super(Contract, self)._convert_contract_lines(contract)
        for (_0, _0, vals), contract_line in zip(
                new_lines, contract.recurring_invoice_line_ids):
            vals["contract_template_line_id"] = contract_line.id
            vals.pop("discount_line_ids", None)
        return new_lines

    @api.model
    def _prepare_invoice_line(self, line, invoice_id):
        "Compute discount and append discount description to invoice line name"
        vals = super(Contract, self)._prepare_invoice_line(line, invoice_id)

        date_invoice = fields.Date.from_string(
            line.analytic_account_id.recurring_next_date)
        result = line.compute_discount(date_invoice)

        vals["discount"] = result["total"]
        descriptions = result["descriptions"]
        if descriptions:
            vals["name"] += u"\n" + (_("Applied discounts:\n- %s")
                                     % u"\n- ".join(descriptions))

        return vals

    @api.multi
    def simulate_payments(self):
        self.ensure_one()

        # This is ugly (as is_auto_pay is introduced by contract_payment_auto)
        # BUT it is so dangerous not to unset it in the simulation that we
        # prefer this over more complex and not so secure solutions...
        if getattr(self, 'is_auto_pay', False):
            self.is_auto_pay = False

        max_date = fields.Date.from_string(self.date_start)

        for contract_line in self.recurring_invoice_line_ids:
            for discount_line in contract_line._applicable_discount_lines():
                date_start = discount_line._compute_date(contract_line, "start")
                if date_start > max_date:
                    max_date = date_start
                if discount_line.end_value:
                    date_end = discount_line._compute_date(contract_line, "end")
                    if date_end > max_date:
                        max_date = date_start

        lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])

        inv_data = []
        last_amount = None

        point_name = uuid.uuid1().hex
        self.env.cr.execute('SAVEPOINT "%s"' % point_name)
        try:
            while fields.Date.from_string(self.recurring_next_date) <= max_date:
                inv = self.recurring_create_invoice()
                if last_amount != inv.amount_total:
                    last_amount = inv.amount_total
                    data = inv.read()[0]
                    data["invoice_line_ids"] = inv.invoice_line_ids.read()
                    inv_data.append(data)
            return inv_data
        finally:
            self.env.cr.execute('ROLLBACK TO SAVEPOINT "%s"' % point_name)
