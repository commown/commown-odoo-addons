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
        """Take contract variable discounts into account

        This requires special care for cooperative campaigns to avoid lots of http
        requests: the last generated invoice line result for the coop campaign
        discount applicability is reused.

        """
        values = super()._prepare_contract_line_forecast_period(
            period_date_start,
            period_date_end,
            recurring_next_date,
        )

        # Forecast the applicability of cooperative-campaign discounts based on the
        # its result on the last generated invoice line:
        coop_camp_discounts = [
            dl
            for dl in self._applicable_discount_lines()
            if dl.coupon_campaign_id and dl.coupon_campaign_id.is_coop_campaign
        ]
        bypass_coop_campaigns = self.last_invoice_discount_state(*coop_camp_discounts)

        # Compute all discounts and apply them to the forecast:
        discount_values = self.with_context(
            bypass_coop_campaigns=bypass_coop_campaigns
        ).compute_discount(period_date_start)

        values["discount"] = discount_values["total"]
        if discount_values["discounts"]:
            values["name"] += "\n" + (
                _("Applied discounts:\n- %s")
                % "\n- ".join(d.name for d in discount_values["discounts"])
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

    def regenerate_forecast_if_conditional_discounts_changed(self):
        """Regenerate forecasts if some discounts changed between last 2 invoices

        This is needed for conditional discounts (e.g. TeleCommown or no_issue_to_date)
        which are by nature unpredictable: in this case, the last value of its
        applicability/ inapplicability is reused as a forecast (the best possible).
        """

        self.ensure_one()

        inv_lines = self._last_invoices_self_generated_line(limit=2)
        if len(inv_lines) != 2:
            return

        invl1, invl2 = inv_lines
        discounts1 = {d for d in invl1.applied_discounts() if d.condition}
        discounts2 = {d for d in invl2.applied_discounts() if d.condition}
        if discounts1 != discounts2:
            self._generate_forecast_periods()
