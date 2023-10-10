from odoo import _, api, models


class ContractLine(models.Model):

    _inherit = "contract.line"

    @api.multi
    def _prepare_contract_line_forecast_period(
        self, period_date_start, period_date_end, recurring_next_date
    ):
        values = super()._prepare_contract_line_forecast_period(
            period_date_start,
            period_date_end,
            recurring_next_date,
        )

        # By-pass cooperative campaigns discount computations
        discount_values = self.with_context(is_simulation=True).compute_discount(
            period_date_start
        )

        values["discount"] = discount_values["total"]
        if discount_values["descriptions"]:
            values["name"] += "\n" + (
                _("Applied discounts:\n- %s")
                % "\n- ".join(discount_values["descriptions"])
            )

        return values

    @api.model
    def _get_forecast_update_trigger_fields(self):
        fields = super()._get_forecast_update_trigger_fields()
        fields.remove("recurring_next_date")
        return fields
