from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests.common import at_install, post_install

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC
from odoo.addons.queue_job.tests.common import trap_jobs


@at_install(False)
@post_install(True)
class CommownContractForecastFunctionalTC(RentalSaleOrderTC):
    def setUp(self):
        "Revert synchronous job definition - Should refactor this!"
        super().setUp()

        self.env = self.env(
            context=dict(
                self.env.context,
                test_queue_job_no_delay=False,
            )
        )

    def test_contract_life_cycle(self):
        "Forecast computations should be triggered when (and only when) needed"

        # Enforce test prerequisites
        company = self.env.user.partner_id.company_id
        company.update(
            {
                "enable_contract_forecast": True,
                "contract_forecast_interval": 15,
                "contract_forecast_rule_type": "monthly",
            }
        )

        # Check no forecasts get created on contract creation
        # as we create it in the far future...
        with trap_jobs() as trap:
            so = self.create_sale_order()
            so.action_confirm()

        self.assertEqual(len(trap.enqueued_jobs), 0)

        contracts = self.env["contract.contract"].of_sale(so)
        contract_lines = contracts.mapped("contract_line_ids")

        # Check forecasts get created on contract real start
        new_date_start = date.today()
        with trap_jobs() as trap:
            contracts.update({"date_start": new_date_start})

        self.assertEqual(len(trap.enqueued_jobs), len(contract_lines))
        trap.perform_enqueued_jobs()

        self.assertEqual(
            company.contract_forecast_interval * len(contract_lines),
            self.env["contract.line.forecast.period"].search_count([]),
        )

        # Check forecasts get recomputed on contract invoice creation
        with trap_jobs() as trap:
            with trap_jobs() as trap_create_invoice:
                contracts._recurring_create_invoice()
            trap_create_invoice.perform_enqueued_jobs()

        self.assertEqual(len(trap.enqueued_jobs), len(contract_lines))
        trap.perform_enqueued_jobs()

        self.assertEqual(
            (company.contract_forecast_interval - 1) * len(contract_lines),
            self.env["contract.line.forecast.period"].search_count([]),
        )

        # Check forecasts get recomputed on discount addition
        # (on contract or contract template)
        # XXX code me

        # Check forecasts get recomputed on contract programmed end
        new_duration = relativedelta(months=7, days=-1)
        with trap_jobs() as trap:
            contract_lines.update(
                {"date_end": contract_lines[0].recurring_next_date + new_duration}
            )

        self.assertEqual(len(trap.enqueued_jobs), len(contract_lines))
        trap.perform_enqueued_jobs()

        self.assertEqual(
            new_duration.months * len(contract_lines),
            self.env["contract.line.forecast.period"].search_count([]),
        )
