from odoo import _, api, models

from odoo.addons.queue_job.job import identity_exact


class ContractLine(models.Model):

    _inherit = "contract.line"

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

    @api.multi
    def generate_forecast_periods(self):
        "Don't generate forecasts when creating a contract from sale in product_rental"
        if not "contract_descr" in self.env.context:
            for contract_line in self:
                if contract_line.contract_id.company_id.enable_contract_forecast:
                    contract_line.with_delay(
                        identity_key=identity_exact
                    )._generate_forecast_periods()
