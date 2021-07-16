# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _name = "contract.template.abstract.discount.line"
    _description = u"Contract template variable discount line"

    name = fields.Char(required=True, translate=True)

    condition = fields.Selection(
        [],
        string=u"Condition of this discount applicability",
        help=u"If empty: discount line always apply",
        required=False,
    )

    amount_type = fields.Selection(
        [("fix", u"Fixed"),
         ("percent", u"Percentage")],
        string=u"Amount type",
        default="percent",
        required=True,
    )

    amount_value = fields.Float(
        string=u"Amount value",
        help=u"A positive amount indicates a price discount",
        required=True,
    )

    start_value = fields.Integer(
        string=u"Value",
        default=0,
        required=True,
    )

    start_reference = fields.Selection(
        [("date_start", "Contract start date")],
        default="date_start",
        string=u"Start reference date",
        help=u"Date reference used to compute the discount start date",
        required=True,
    )

    start_unit = fields.Selection(
        [("days", u"Days"),
         ("weeks", u"Weeks"),
         ("months", u"Months"),
         ("years", u"Years")],
        string=u"Units",
        help=u"Units of the discount start difference with the reference date",
        default="months",
        required=True,
    )

    end_value = fields.Integer(
        string=u"Value",
        help=u"No value means no end for this discount",
    )

    end_reference = fields.Selection(
        [("date_start", "Contract start date")],
        default="date_start",
        string=u"End reference date",
        help=u"Date reference used to compute the discount end date",
        required=True,
    )

    end_unit = fields.Selection(
        [("days", u"Days"),
         ("weeks", u"Weeks"),
         ("months", u"Months"),
         ("years", u"Years")],
        string=u"Units",
        help=u"Units of the discount end difference with the reference date",
        default="months",
        required=True,
    )

    @api.multi
    def compute(self, contract_line, date_invoice):
        " Return the actual discount for given contract line and invoice date "

        self.ensure_one()

        if (self._condition_ok(contract_line, date_invoice)
                and self._start_date_ok(contract_line, date_invoice)
                and self._end_date_ok(contract_line, date_invoice)):
            return self._compute_amount(contract_line, date_invoice)

    def _compute_amount(self, contract_line, date_invoice):
        if self.amount_type == "fix":
            discount = 100. * self.amount_value / contract_line.price_unit
        elif self.amount_type == "percent":
            discount = self.amount_value
        else:
            raise ValidationError(
                _("Invalid discount amount type '%s' for contract %s")
                % (self.amount_type, contract_line.analytic_account_id.name))
        return discount

    def _compute_date(self, contract_line, date_attr_prefix):
        contract = contract_line.analytic_account_id
        cfields = contract.fields_get()

        reference = getattr(self, "%s_reference" % date_attr_prefix)
        if reference not in cfields or cfields[reference]["type"] != "date":
            raise ValidationError(
                _("Incorrect reference '%s' in discount date of contract %s")
                % (reference, contract.name))

        reference_date = getattr(contract, reference)
        if not reference_date:
            raise ValidationError(
                _("Incorrect reference date value for '%s' of contract %s")
                % (reference, contract.name))

        unit = getattr(self, "%s_unit" % date_attr_prefix)
        value = getattr(self, "%s_value" % date_attr_prefix)

        return fields.Date.from_string(reference_date) + relativedelta(
            **{unit: value})

    def _start_date_ok(self, contract_line, date_invoice):
        date_start = self._compute_date(contract_line, "start")
        return date_start <= date_invoice

    def _end_date_ok(self, contract_line, date_invoice):
        if not self.end_value:
            return True
        else:
            date_end = self._compute_date(contract_line, "end")
        return date_end > date_invoice

    def _condition_ok(self, contract_line, date_invoice):
        if not self.condition:
            return True
        meth = getattr(self, "_compute_condition_%s" % self.condition, None)
        if meth is None:
            raise ValidationError(
                _("Invalid discount condition %s in contract %s")
                % (self.condition, contract_line.analytic_account_id.name))
        return meth(contract_line, date_invoice)


class ContractTemplateDiscountLine(models.Model):
    _name = "contract.template.discount.line"
    _inherit = "contract.template.abstract.discount.line"

    contract_template_line_id = fields.Many2one(
        comodel_name="account.analytic.contract.line",
        string="Contract template line",
        required=False,
        copy=False,
    )


class ContractDiscountLine(models.Model):

    _name = "contract.discount.line"
    _inherit = "contract.template.abstract.discount.line"
    _description = u"Contract discount line"

    contract_line_id = fields.Many2one(
        comodel_name="account.analytic.invoice.line",
        string="Contract line",
        required=False,
        copy=False,
    )

    replace_discount_line_id = fields.Many2one(
        comodel_name="contract.template.discount.line",
        string=u"Replace discount line",
        help=(u"If a discount line is added here, it will no more apply"
              " but be replaced by current line"),
        required=False,
        domain="[('id', 'in', contract_line_id.contract_template_line_id.discount_line_ids.ids)]",
    )
