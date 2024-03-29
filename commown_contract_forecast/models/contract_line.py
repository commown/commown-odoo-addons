from odoo import _, api, models

from odoo.addons.queue_job.job import identity_exact


class ContractLine(models.Model):

    _inherit = "contract.line"

    @api.model
    def cron_recompute_forecasts(self, batch_size=100):
        self.env["contract.line.forecast.period"].search([]).unlink()
        offset = 0
        while True:
            contract_lines = self.search(
                [("is_canceled", "=", False)],
                limit=batch_size,
                offset=offset,
            )
            contract_lines.generate_forecast_periods()
            if len(contract_lines) < batch_size:
                break
            offset += batch_size

    @api.multi
    def _prepare_contract_line_forecast_period(
        self, period_date_start, period_date_end, recurring_next_date
    ):
        "Take contract variable discounts into account"
        values = super()._prepare_contract_line_forecast_period(
            period_date_start,
            period_date_end,
            recurring_next_date,
        )

        # By-pass cooperative campaigns discount computations
        discount_values = self.with_context(
            bypass_coop_campaigns=True
        ).compute_discount(period_date_start)

        values["discount"] = discount_values["total"]
        if discount_values["descriptions"]:
            values["name"] += "\n" + (
                _("Applied discounts:\n- %s")
                % "\n- ".join(discount_values["descriptions"])
            )

        return values

    @api.model
    def _get_forecast_update_trigger_fields(self):
        result = super()._get_forecast_update_trigger_fields()
        result.append("specific_discount_line_ids")
        return result

    @api.multi
    def generate_forecast_periods(self):
        "Don't generate forecasts when creating a contract from sale in product_rental"
        if "contract_descr" not in self.env.context:
            for contract_line in self:
                if contract_line.contract_id.company_id.enable_contract_forecast:
                    contract_line.with_delay(
                        identity_key=identity_exact
                    )._generate_forecast_periods()
