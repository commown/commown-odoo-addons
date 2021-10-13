from functools import partial
from datetime import datetime, timedelta

import pytz
import requests_mock

from odoo.fields import Date

from odoo.addons.commown_cooperative_campaign.models.discount import (
    partner_identifier)
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
        self.customer_key = partner_identifier(self.so.partner_id, self.campaign)

    def invoice(self, optin, optout=None, mock_optin=False):
        """ Create an invoice from contract mocking the cooperative web service
        with give optin and optout dates generators.
        """
        date = self.contract.recurring_next_date

        events = [{"type": "optin", "ts": optin(date)}]
        if optout is not None:
            events.append({"type": "optout", "ts": optout(date)})

        with requests_mock.Mocker() as rm:
            rm.get("/campaign/test-campaign/subscriptions/important-events/",
                   json=[{"events": events}])
            if mock_optin:
                rm.post("/campaign/test-campaign/opt-in/", json={
                    "id": 1, "campaign": {}, "member": {},
                    "optin_ts": ts_after(self.contract.recurring_next_date, 0),
                    "optout_ts": None,
                })
            invoice = self.contract.recurring_create_invoice()
        reqs = rm.request_history
        if mock_optin:
            self.assertEqual(reqs[0].path, "/campaign/test-campaign/opt-in/")
            self.assertEqual(reqs[0].json(), {
                u'customer_key': self.customer_key,
                u'optin_ts': ts_after(invoice.date_invoice, 0),
            })

        self.assertEqual(
            reqs[-1].path,
            "/campaign/test-campaign/subscriptions/important-events/")
        self.assertEqual(reqs[-1].query, u"customer_key=%s" % self.customer_key)
        return invoice

    def test_invoices(self):
        before7 = partial(ts_before, days=7)
        before1 = partial(ts_before, days=1)
        self.assertEqual(self.invoice(before1, mock_optin=True).amount_total, 6.9)
        self.assertEqual(self.invoice(before1, ts_after).amount_total, 6.9)
        self.assertEqual(self.invoice(before7, before1).amount_total, 34.5)
        self.assertEqual(self.invoice(ts_after).amount_total, 34.5)

    def test_contract_end(self):
        inv = self.invoice(partial(ts_before, days=7), mock_optin=True)
        date_end = Date.to_string(Date.from_string(inv.date_invoice)
                                  + timedelta(days=10))
        with requests_mock.Mocker() as rm:
            rm.post("/campaign/test-campaign/opt-out/", json={
                "id": 1, "campaign": {}, "member": {},
                "optin_ts": ts_before(inv.date_invoice, 0),
                "optout_ts": ts_after(date_end, 0),
            })
            self.contract.update({'date_end': date_end})
            self.contract.onchange_date_end()

        self.assertEqual(rm.request_history[0].path,
                         "/campaign/test-campaign/opt-out/")
        self.assertEqual(rm.request_history[0].json(), {
            u'customer_key': self.customer_key,
            u'optout_ts': ts_after(date_end, 0),
            })
