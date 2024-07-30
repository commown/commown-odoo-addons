from dateutil.relativedelta import relativedelta

from odoo import tools
from odoo.modules.module import get_resource_path
from odoo.tests.common import at_install, post_install

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC
from odoo.addons.queue_job.tests.common import trap_jobs

from .common import fake_today


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

        if not self.env["account.journal"].search([("type", "=", "sale")]):
            # When running in a db where the commown module is not installed
            # (=not the in the CI), no dependency module sets up accounting
            # and invoice generation crashes; following inserts the minimal
            # data needed to avoid this:
            tools.convert_file(
                self.cr,
                "commown_contract_forecast",
                get_resource_path("account", "test", "account_minimal_test.xml"),
                {},
                "init",
                False,
                "test",
                self.registry._assertion_report,
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
        with trap_jobs() as trap:
            contracts.update({"date_start": fake_today()})

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

        # Check forecasts get recomputed on discount addition...
        cdiscount_model = self.env["contract.discount.line"]
        ctdiscount_model = self.env["contract.template.discount.line"]
        discount_data = {
            "name": "1 year loyalty",
            "amount_type": "percent",
            "amount_value": 10.0,
            "start_reference": "date_start",
            "start_value": 1,
            "start_unit": "years",
            "end_type": "relative",
            "end_reference": "date_start",
            "end_value": 2,
            "end_unit": "years",
        }

        # - ... to a contract
        cline0 = contract_lines[0]
        with trap_jobs() as trap:
            cline0.specific_discount_line_ids = cdiscount_model.create(
                dict(discount_data, contract_line_id=cline0.id)
            )

        self.assertEqual(len(trap.enqueued_jobs), 1)
        trap.perform_enqueued_jobs()
        self.assertEqual(
            cline0.mapped("forecast_period_ids.discount")[-4:],
            [0.0, 10.0, 10.0, 10.0],
        )

        # - ... to a contract template
        # Choose the CT used for the 2 PCs of the `so` sale order and check a forecast
        # is recomputed for both 2 impacted contract lines prices
        clines = contract_lines.filtered(
            lambda cl: cl.sale_order_line_id.product_id.name == "PC"
        )
        self.assertEqual(len(clines), 2)

        ctline = clines.mapped("contract_template_line_id")
        self.assertEqual(len(ctline), 1)

        with trap_jobs() as trap:
            ctline.discount_line_ids = ctdiscount_model.create(
                dict(discount_data, contract_template_line_id=ctline.id)
            )

        self.assertEqual(len(trap.enqueued_jobs), len(clines))
        trap.perform_enqueued_jobs()

        for cline in clines:
            self.assertEqual(
                cline.mapped("forecast_period_ids.discount")[-4:],
                [0.0, 10.0, 10.0, 10.0],
            )

        # Check forecasts get synchronously recomputed on dedication action use:
        contract = contract_lines[0].contract_id
        old_forecasts = contract.mapped("contract_line_ids.forecast_period_ids")
        self.assertTrue(old_forecasts.exists(), "Test pre-requisite")
        contract.action_regenerate_forecast()
        self.assertFalse(old_forecasts.exists())
        self.assertTrue(contract.mapped("contract_line_ids.forecast_period_ids"))

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
