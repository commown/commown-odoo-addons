from datetime import date

from odoo import _, api, models


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.multi
    def displayable_key_value(self, key, value):
        "Let a chance for i18n to reformat 'key: value' into e.g. 'key : value'"
        return _(" - %(descr_key)s: %(descr_value)s") % {
            "descr_key": key,
            "descr_value": value,
        }

    @api.multi
    def displayable_description(self):
        "Return a dict description in customer's lang"
        self.ensure_one()

        lang = self.env["res.lang"].search([("code", "=", self.env.user.lang)])
        date_format = lang.date_format or "%Y-%m-%d"
        order_id = self.mapped("contract_line_ids.sale_order_line_id.order_id").id

        result = {
            "start_date": self.date_start.strftime(date_format),
            "commitment_end_date": self.commitment_end_date.strftime(date_format),
            "in_commitment": date.today() < self.commitment_end_date,
            "order_id": order_id or "",
        }

        fields = self.fields_get()

        result["descr"] = self.name + self.displayable_key_value(
            fields["date_start"]["string"],
            result["start_date"],
        )

        if result["in_commitment"]:
            result["descr"] += self.displayable_key_value(
                fields["commitment_end_date"]["string"],
                result["commitment_end_date"],
            )

        return result
