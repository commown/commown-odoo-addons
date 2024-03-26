from datetime import datetime, timedelta

import pytz
import requests_mock

from odoo.addons.commown_contract_variable_discount.tests.common import (
    ContractSaleWithCouponTC,
)


def ts_after(date, days=7, hour=9):
    "Generate a date in iso format from given odoo string date + given days"
    return (
        datetime(date.year, date.month, date.day, hour, tzinfo=pytz.utc)
        + timedelta(days=days)
    ).isoformat()


def ts_before(date, days=7):
    "Generate a date in iso format from given odoo string date - given days"
    return ts_after(date, -days)


class CooperativeCampaignTC(ContractSaleWithCouponTC):
    def setUp(self):
        super(CooperativeCampaignTC, self).setUp()

        # Force querying the cooperative web service:
        self.campaign.update(
            {
                "is_coop_campaign": True,
                "cooperative_salt": "no matter",
            }
        )

        # This is required for partner "anon" identifier generation:
        self.so.partner_id.phone = "0677889900"
        self.so.partner_id.country_id = self.env.ref("base.fr").id
        self.customer_key = self.campaign.coop_partner_identifier(self.so.partner_id)

    def invoice(
        self,
        optin,
        optout=None,
        mock_optin=False,
        check_mock_calls=True,
        env=None,
    ):
        """Create an invoice from contract mocking the cooperative web service
        with give optin and optout dates generators.
        """
        if env is None:
            contract = self.contract
        else:
            contract = env["contract.contract"].browse(self.contract.id)

        date = contract.recurring_next_date

        events = [{"type": "optin", "ts": optin(date)}]
        if optout is not None:
            events.append({"type": "optout", "ts": optout(date)})

        with requests_mock.Mocker() as rm:
            rm.get(
                "/campaigns/test-campaign/subscriptions/important-events",
                json=[{"events": events}],
            )
            if mock_optin:
                rm.post(
                    "/campaigns/test-campaign/opt-in",
                    json={
                        "id": 1,
                        "campaign": {},
                        "member": {},
                        "optin_ts": ts_after(contract.recurring_next_date, 0),
                        "optout_ts": None,
                    },
                )
            invoice = contract.recurring_create_invoice()

        if check_mock_calls:
            reqs = rm.request_history

            if mock_optin:
                self.assertEqual(reqs[0].path, "/campaigns/test-campaign/opt-in")
                self.assertEqual(
                    reqs[0].json(),
                    {
                        "customer_key": self.customer_key,
                        "optin_ts": ts_after(invoice.date_invoice, 0),
                    },
                )
            else:
                self.assertEqual(len(reqs), 1)
            self.assertEqual(
                reqs[-1].path, "/campaigns/test-campaign/subscriptions/important-events"
            )
            self.assertEqual(reqs[-1].query, "customer_key=" + self.customer_key)

        return invoice
