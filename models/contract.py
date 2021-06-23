# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import OrderedDict

import yaml
from yaml.error import YAMLError

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    """ Load yaml mappings into ordered dicts to ease testing """

    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    return yaml.load(stream, OrderedLoader)


class ContractTemplateLine(models.Model):
    _inherit = "account.analytic.contract.line"

    discount_formula = fields.Text("Discount formula")

    @api.constrains('discount_formula')
    def _check_discount_formula(self):
        for record in self:
            if record.discount_formula:
                try:
                    # no need to use ordered_load here
                    yaml.load(record.discount_formula)
                except YAMLError as exc:
                    raise ValidationError(
                        _('Invalid YAML (detail below):\n%s') % str(exc))


class Contract(models.Model):
    _inherit = "account.analytic.account"
    discount_date_units = {"days", "weeks", "months", "years"}

    @api.model
    def _prepare_invoice_line(self, line, invoice_id):
        "Override to compute discount and append discount description to name"
        vals = super(Contract, self)._prepare_invoice_line(line, invoice_id)
        if line.discount_formula:
            date_invoice = fields.Date.from_string(
                line.analytic_account_id.recurring_next_date)
            result = self.discount_formula_compute(line, date_invoice)
            vals["discount"] = result["discount"]
            vals["name"] += u"\n" + result["customer_description"]
        return vals

    def _discount_formula_amount(self, line, date_invoice, amount_descr):
        if amount_descr["type"] == "fix":
            discount = 100. * amount_descr["value"] / line.price_unit
        elif amount_descr["type"] == "percent":
            discount = amount_descr["value"]
        else:
            raise ValidationError
        return discount

    def _discount_formula_date(self, line, date_invoice, date_descr):
        contract = line.analytic_account_id
        cfields = contract.fields_get()

        reference = date_descr.get("reference", "date_start")
        if reference not in cfields or cfields[reference]["type"] != "date":
            raise ValidationError(
                _("Incorrect reference '%s' in discount date of contract %s")
                % (reference, contract.name))

        reference_date = getattr(contract, reference)
        if not reference_date:
            raise ValidationError(
                _("Incorrect reference date value for '%s' of contract %s")
                % (reference, contract.name))

        if "unit" not in date_descr:
            raise ValidationError(
                _("Missing unit in discount date of contract %s")
                % contract.name)
        unit = date_descr["unit"]
        if unit not in self.discount_date_units:
            raise ValidationError(
                _("Invalid unit '%s' in discount date of contract %s")
                % (unit, contract.name))

        if "value" not in date_descr:
            raise ValidationError(
                _("Missing value to discount date definition in contract %s")
                % contract.name)
        value = date_descr["value"]
        if type(value) is not int:
            raise ValidationError(
                _("Invalid value %r in discount date of contract %s")
                % (value, contract.name))

        return fields.Date.from_string(reference_date) + relativedelta(
            **{unit: value})

    def _discount_formula_condition(self, line, date_invoice, condition):
        meth = getattr(self, "_discount_formula_condition_%s" % condition, None)
        if meth is None:
            raise ValidationError(
                _("Invalid discount condition %s in contract %s")
                % (condition, line.analytic_account_id.name))
        return meth(line, date_invoice)

    @api.model
    def discount_formula_compute(self, line, date_invoice):
        total_discount = 0
        customer_description = []

        for name, descr in ordered_load(line.discount_formula).items():

            if ("condition" in descr
                and not self._discount_formula_condition(
                    line, date_invoice, descr["condition"])):
                continue

            if ("start" in descr
                and self._discount_formula_date(
                    line, date_invoice, descr["start"]) > date_invoice
               ):
                continue

            if ("end" in descr
                and self._discount_formula_date(
                    line, date_invoice, descr["end"]) <= date_invoice
               ):
                continue

            total_discount += self._discount_formula_amount(
                line, date_invoice, descr["amount"])
            customer_description.append(name)

        return {
            "discount": total_discount,
            "customer_description": u"\n".join(customer_description),
        }
