from odoo import api, models


class ContractLine(models.Model):

    _inherit = "contract.line"

    @api.model
    def _get_forecast_update_trigger_fields(self):
        res = super()._get_forecast_update_trigger_fields()
        if "recurring_next_date" in res:
            res.remove("date_start")  # Avoid doubled trigger with recurring_next_date
        return res
