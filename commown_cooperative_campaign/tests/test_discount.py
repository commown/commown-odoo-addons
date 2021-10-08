from functools import partial
from datetime import datetime, timedelta

import pytz
import requests_mock

from odoo.fields import Date
from odoo.addons.commown_contract_variable_discount.tests.common import (
    ContractSaleWithCouponTC)


def ts_after(date, days=7):
    "Generate a date in iso format from given odoo string date + given days"
    _date = Date.from_string(date)
    return (datetime(_date.year, _date.month, _date.day, tzinfo=pytz.utc)
            + timedelta(days=days)).isoformat()


def ts_before(date, days=7):
    "Generate a date in iso format from given odoo string date - given days"
    return ts_after(date, -days)


class CooperativeCampignTC(ContractSaleWithCouponTC):

    def invoice(self, optin, optout=None):
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
            return self.contract.recurring_create_invoice()

    def test(self):
        # Force querying the cooperative web service:
        self.campaign.is_coop_campaign = True

        # This is required for partner "anon" identifier generation:
        self.so.partner_id.phone = u"0677889900"
        self.so.partner_id.country_id = self.env.ref("base.fr").id

        # Perform the tests:
        before7 = partial(ts_before, days=7)
        before1 = partial(ts_before, days=1)
        self.assertEqual(self.invoice(before1).amount_total, 6.9)
        self.assertEqual(self.invoice(before1, ts_after).amount_total, 6.9)
        self.assertEqual(self.invoice(before7, before1).amount_total, 34.5)
        self.assertEqual(self.invoice(ts_after).amount_total, 34.5)
