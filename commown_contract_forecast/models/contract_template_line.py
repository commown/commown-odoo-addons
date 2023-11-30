from odoo import api, models


class ContractTemplateLine(models.Model):
    _inherit = "contract.template.line"

    @api.multi
    def write(self, values):
        "Recompute contract forecasts when discount lines change"
        result = super().write(values)

        if "discount_line_ids" in values:
            clines = self.env["contract.line"].search(
                [
                    ("contract_template_line_id", "in", self.ids),
                    ("date_start", "<=", "TODAY"),
                    "|",
                    ("date_end", "=", False),
                    ("date_end", ">", "TODAY"),
                ]
            )
            clines.generate_forecast_periods()

        return result
