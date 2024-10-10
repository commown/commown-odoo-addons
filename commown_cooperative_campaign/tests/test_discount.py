from datetime import timedelta
from functools import partial

import mock
import requests
import requests_mock
from requests_mock.exceptions import NoMockAddress

from odoo.fields import Date
from odoo.tools import mute_logger

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import CooperativeCampaignTC, ts_after, ts_before


class DiscountCooperativeCampaignTC(CooperativeCampaignTC):
    def test_invoices(self):
        before7 = partial(ts_before, days=7)
        before1 = partial(ts_before, days=1)
        inv1 = self.invoice(before1, mock_optin=True)
        self.assertEqual(
            self.contract.contract_line_ids.last_invoice_cooperative_discount_state(),
            {inv1.invoice_line_ids.applied_discount_template_line_ids: True},
        )
        self.assertEqual(inv1.amount_untaxed, 6.0)
        self.assertEqual(self.invoice(before1, ts_after).amount_untaxed, 6.0)
        self.assertEqual(self.invoice(before7, before1).amount_untaxed, 30.0)
        # opt-in mock is not called below as the end date of the discount is reached
        self.assertEqual(
            self.invoice(ts_after, check_mock_calls=False).amount_untaxed, 30.0
        )

    def test_invoice_no_identifier(self):
        "Partners having no phone or country do not benefit from the discount"
        self.so.partner_id.phone = False
        before1 = partial(ts_before, days=1)
        with mute_logger("odoo.addons.commown_cooperative_campaign.models.discount"):
            self.assertEqual(
                self.invoice(before1, check_mock_calls=False).amount_untaxed, 30.0
            )

    def test_invoice_double_optin(self):
        "Double-optin specific 422 error must not raise"
        with requests_mock.Mocker() as rm:
            rm.post(
                "/campaigns/test-campaign/opt-in",
                status_code=422,
                json={"detail": "Already opt-in"},
            )

            event = {
                "type": "optin",
                "ts": ts_before(self.contract.recurring_next_date),
            }
            rm.get(
                "/campaigns/test-campaign/subscriptions/important-events",
                json=[{"events": [event]}],
            )

            invoice = self.contract.recurring_create_invoice()

        self.assertEqual(invoice.amount_untaxed, 6.0)

    @mute_logger("odoo.addons.commown_cooperative_campaign.models.discount")
    def test_invoice_optin_error_any_422(self):
        "422 HTTP errors other than double optin must raise"
        with self.assertRaises(requests.HTTPError):
            with requests_mock.Mocker() as rm:
                response = mock.Mock(
                    status_code=422, json=lambda: {"detail": "Unknown error"}
                )
                rm.post(
                    "/campaigns/test-campaign/opt-in",
                    exc=requests.HTTPError(response=response),
                )
                self.contract.recurring_create_invoice()

    def test_invoice_optin_error_timeout(self):
        "All other HTTP errors must raise"
        with self.assertRaises(requests.ConnectTimeout):
            with requests_mock.Mocker() as rm:
                rm.post("/campaigns/test-campaign/opt-in", exc=requests.ConnectTimeout)
                self.contract.recurring_create_invoice()

    def _set_contract_date_end(self, date_end, check_job=True):
        with trap_jobs() as trap:
            self.contract.date_end = date_end

        if check_job:
            trap.assert_jobs_count(1, only=self.contract._coop_ws_optout)

        trap.perform_enqueued_jobs()

    def test_contract_end(self):
        inv = self.invoice(partial(ts_before, days=7), mock_optin=True)
        date_end = inv.date_invoice + timedelta(days=10)
        with requests_mock.Mocker() as rm:
            rm.post(
                "/campaigns/test-campaign/opt-out",
                json={
                    "id": 1,
                    "campaign": {},
                    "member": {},
                    "optin_ts": ts_before(inv.date_invoice, 0),
                    "optout_ts": ts_after(date_end, 0),
                },
            )
            self._set_contract_date_end(date_end)

        self.assertEqual(rm.request_history[0].path, "/campaigns/test-campaign/opt-out")
        self.assertEqual(
            rm.request_history[0].json(),
            {
                "customer_key": self.customer_key,
                "optout_ts": ts_after(date_end, 0),
            },
        )

        # Check that nothing crashes when partner has no customer_key
        self.contract.partner_id.update({"phone": False, "mobile": False})
        date_end = Date.to_string(
            Date.from_string(self.contract.date_end) + timedelta(days=10)
        )
        with requests_mock.Mocker() as rm:
            # Should never call the service
            rm.post(
                "/campaigns/test-campaign/opt-out",
                exc=Exception("Test failure: service should not be called"),
            )
            self._set_contract_date_end(date_end, check_job=False)

    def test_bypass_coop_campaigns(self):
        "Don't call optin WS when bypass_coop_campaigns is in the context"

        def do_test(env):
            before1 = partial(ts_before, days=1)
            return self.invoice(
                before1, mock_optin=False, check_mock_calls=False, env=env
            )

        # Check test prequisite without modifying the DB, to revert the side effect of
        # this check (which otherwise would create an invoice and prevent a new optin
        # call when repeating):
        with self.env.cr.savepoint():
            with self.assertRaises(NoMockAddress) as err:
                do_test(self.env)
        self.assertTrue(err.exception.request.url.endswith("/opt-in"))

        # Same call with same DB state but with the bypass_coop_campaigns context
        # variable should not raise (important-events is mocked here!):
        bypass = dict.fromkeys(
            self.contract.contract_line_ids._applicable_discount_lines(),
            True,
        )
        env = self.env(context=dict(self.env.context, bypass_coop_campaigns=bypass))
        invoice = do_test(env)
        self.assertIn("Test coupon discount", invoice.invoice_line_ids.name)
