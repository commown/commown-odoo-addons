from functools import partial
from datetime import datetime, timedelta

import mock
import pytz
import requests
import requests_mock

from odoo.fields import Date

from odoo.addons.commown_contract_variable_discount.tests.common import (
    ContractSaleWithCouponTC)


def ts_after(date, days=7, hour=9):
    "Generate a date in iso format from given odoo string date + given days"
    _date = Date.from_string(date)
    return (datetime(_date.year, _date.month, _date.day, hour, tzinfo=pytz.utc)
            + timedelta(days=days)).isoformat()


def ts_before(date, days=7):
    "Generate a date in iso format from given odoo string date - given days"
    return ts_after(date, -days)


class CooperativeCampaignTC(ContractSaleWithCouponTC):

    def setUp(self):
        super(CooperativeCampaignTC, self).setUp()

        # Force querying the cooperative web service:
        self.campaign.is_coop_campaign = True

        # This is required for partner "anon" identifier generation:
        self.so.partner_id.phone = u"0677889900"
        self.so.partner_id.country_id = self.env.ref("base.fr").id
        self.env["keychain.account"].create({
            "namespace": u"telecommown",
            "name": u"Salt for partner identifiers",
            "technical_name": self.campaign.name + u"-salt",
            "clear_password": u"no-matter",
        })
        self.customer_key = self.campaign.coop_partner_identifier(
            self.so.partner_id)

    def invoice(self, optin, optout=None, mock_optin=False,
                check_mock_calls=True):
        """ Create an invoice from contract mocking the cooperative web service
        with give optin and optout dates generators.
        """
        date = self.contract.recurring_next_date

        events = [{"type": "optin", "ts": optin(date)}]
        if optout is not None:
            events.append({"type": "optout", "ts": optout(date)})

        with requests_mock.Mocker() as rm:
            rm.get("/campaigns/test-campaign/subscriptions/important-events",
                   json=[{"events": events}])
            if mock_optin:
                rm.post("/campaigns/test-campaign/opt-in", json={
                    "id": 1, "campaign": {}, "member": {},
                    "optin_ts": ts_after(self.contract.recurring_next_date, 0),
                    "optout_ts": None,
                })
            invoice = self.contract.recurring_create_invoice()

        if check_mock_calls:
            reqs = rm.request_history

            if mock_optin:
                self.assertEqual(reqs[0].path,
                                 "/campaigns/test-campaign/opt-in")
                self.assertEqual(reqs[0].json(), {
                    u'customer_key': self.customer_key,
                    u'optin_ts': ts_after(invoice.date_invoice, 0),
                })

            self.assertEqual(
                reqs[-1].path,
                "/campaigns/test-campaign/subscriptions/important-events")
            self.assertEqual(reqs[-1].query,
                             u"customer_key=" + self.customer_key)

        return invoice

    def test_invoices(self):
        before7 = partial(ts_before, days=7)
        before1 = partial(ts_before, days=1)
        self.assertEqual(self.invoice(before1, mock_optin=True).amount_total,
                         6.9)
        self.assertEqual(self.invoice(before1, ts_after).amount_total, 6.9)
        self.assertEqual(self.invoice(before7, before1).amount_total, 34.5)
        self.assertEqual(self.invoice(ts_after).amount_total, 34.5)

    def test_invoice_no_identifier(self):
        "Partners having no phone or country do not benefit from the discount"
        self.so.partner_id.phone = False
        before1 = partial(ts_before, days=1)
        self.assertEqual(
            self.invoice(before1, check_mock_calls=False).amount_total, 34.5)

    def test_invoice_double_optin(self):
        "Double-optin specific 422 error must not raise"
        with requests_mock.Mocker() as rm:
            response = mock.Mock(status_code=422,
                                 json=lambda: {"detail": "Already opt-in"})
            rm.post("/campaigns/test-campaign/opt-in",
                    exc=requests.HTTPError(response=response))

            event = {"type": "optin",
                     "ts": ts_before(self.contract.recurring_next_date)}
            rm.get("/campaigns/test-campaign/subscriptions/important-events",
                   json=[{"events": [event]}])

            invoice = self.contract.recurring_create_invoice()

        self.assertEqual(invoice.amount_total, 6.9)

    def test_invoice_optin_error_any_422(self):
        "422 HTTP errors other than double optin must raise"
        with self.assertRaises(requests.HTTPError):
            with requests_mock.Mocker() as rm:
                response = mock.Mock(status_code=422,
                                     json=lambda: {"detail": "Unknown error"})
                rm.post("/campaigns/test-campaign/opt-in",
                        exc=requests.HTTPError(response=response))
                self.contract.recurring_create_invoice()

    def test_invoice_optin_error_timeout(self):
        "All other HTTP errors must raise"
        with self.assertRaises(requests.ConnectTimeout):
            with requests_mock.Mocker() as rm:
                rm.post("/campaigns/test-campaign/opt-in",
                        exc=requests.ConnectTimeout)
                self.contract.recurring_create_invoice()

    def test_contract_end(self):
        inv = self.invoice(partial(ts_before, days=7), mock_optin=True)
        date_end = Date.to_string(Date.from_string(inv.date_invoice)
                                  + timedelta(days=10))
        with requests_mock.Mocker() as rm:
            rm.post("/campaigns/test-campaign/opt-out", json={
                "id": 1, "campaign": {}, "member": {},
                "optin_ts": ts_before(inv.date_invoice, 0),
                "optout_ts": ts_after(date_end, 0),
            })
            self.contract.update({'date_end': date_end})
            self.contract.onchange_date_end()

        self.assertEqual(rm.request_history[0].path,
                         "/campaigns/test-campaign/opt-out")
        self.assertEqual(rm.request_history[0].json(), {
            u'customer_key': self.customer_key,
            u'optout_ts': ts_after(date_end, 0),
            })
