# Copyright 2023 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields

from odoo.addons.contract.tests.test_contract import TestContractBase
from odoo.addons.queue_job.tests.common import trap_jobs


class ContractLineComputeForecastTC(TestContractBase):
    def cdiscount(self, c_line=None, **kwargs):
        kwargs.setdefault("contract_line_id", (c_line or self.acct_line).id)
        return self.env["contract.discount.line"].create(kwargs)

    def test_forecast_with_discount(self):
        "Check that forecast take discounts into account"

        self.acct_line.specific_discount_line_ids = self.cdiscount(
            name="1 year loyalty",
            amount_type="percent",
            amount_value=10.0,
            start_reference="date_start",
            start_value=1,
            start_unit="years",
            end_type="relative",
            end_reference="date_start",
            end_value=2,
            end_unit="years",
        ) | self.cdiscount(
            name="2 year loyalty",
            amount_type="percent",
            amount_value=20.0,
            start_reference="date_start",
            start_value=2,
            start_unit="years",
            end_type="absolute",
            end_value=False,  # no end
        )

        date = fields.Date.today()
        clines = self.contract.contract_line_ids
        clines.write({"recurring_next_date": date})

        self.contract.partner_id.company_id.update(
            {
                "enable_contract_forecast": True,
                "contract_forecast_rule_type": "monthly",
                "contract_forecast_interval": 36,
            }
        )

        self.assertFalse(self.contract.mapped("contract_line_ids.forecast_period_ids"))

        with trap_jobs() as trap:
            self.contract.date_start = date

        trap.assert_jobs_count(1, only=clines._generate_forecast_periods)
        trap.perform_enqueued_jobs()

        self.assertEqual(
            clines.mapped("forecast_period_ids").mapped("discount"),
            [0.0] * 12 + [10.0] * 12 + [20.0] * 12,
        )
