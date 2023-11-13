from datetime import date

import requests_mock

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


def _date(year, month, day):
    return date(year, month, day).isoformat()


class CouponTestTC(SavepointCase):
    def setUp(self):
        super().setUp()
        campaign = self.env["coupon.campaign"].create(
            {
                "name": "test-campaign",
                "seller_id": 1,
                "is_coop_campaign": True,
                "cooperative_salt": "no matter",
            }
        )
        so = self.env.ref("sale.portal_sale_order_1")
        self.coupon = self.env["coupon.coupon"].create(
            {
                "code": "TEST",
                "campaign_id": campaign.id,
                "used_for_sale_id": so.id,
            }
        )
        self.coupon.used_for_sale_id.partner_id.update(
            {
                "country_id": self.env.ref("base.fr").id,
                "mobile": "0601020304",
            }
        )
        self.key = campaign.coop_partner_identifier(so.partner_id)
        self.paths = {
            "opt-in": "/campaigns/test-campaign/opt-in",
            "important-events": (
                "/campaigns/test-campaign/subscriptions/important-events"
            ),
            "subscriptions": (
                "/campaign/test-campaign/subscriptions?customer_key=%s" % self.key
            ),
        }

    def optin_status(self, important_events, subscriptions=None):
        with requests_mock.Mocker() as rm:
            rm.get(self.paths["important-events"], json=important_events)
            if subscriptions is not None:
                rm.get(self.paths["subscriptions"], json=subscriptions)
            with self.assertRaises(UserError) as err:
                self.coupon.action_coop_campaign_optin_status()
        return err.exception.name.strip()

    def test_action_optin_status_0(self):
        important_events = [{"customer_key": self.key, "events": []}]
        subscriptions = []

        self.assertEqual(
            self.optin_status(important_events, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: not fully subscribed",
                    "--",
                    "No subscription at all (to any partner)",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def test_action_optin_status_1(self):
        important_events = [
            {
                "customer_key": self.key,
                "details": {
                    "telecoop": {"optin_ts": _date(2020, 1, 1), "optout_ts": None},
                },
                "events": [],
            }
        ]
        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "optin_ts": _date(2020, 1, 1),
                "optout_ts": None,
                "member": telecoop,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            }
        ]

        self.assertEqual(
            self.optin_status(important_events, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: not fully subscribed",
                    "--",
                    "Subscription to telecoop: 01/01/2020 00:00:00",
                    "No subscription to commown.",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def test_action_optin_status_2(self):
        important_events = [
            {
                "customer_key": self.key,
                "details": {
                    "commown": {"optin_ts": _date(2019, 12, 25), "optout_ts": None},
                    "telecoop": {"optin_ts": _date(2020, 1, 1), "optout_ts": None},
                },
                "events": [{"type": "optin", "ts": _date(2020, 1, 1)}],
            }
        ]

        self.assertEqual(
            self.optin_status(important_events),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: fully subscribed",
                    "--",
                    "Validity: 01/01/2020 00:00:00",
                    "--",
                    "Key: %s" % self.key,
                    "--",
                    "Details:",
                    "- commown: 12/25/2019 00:00:00",
                    "- telecoop: 01/01/2020 00:00:00",
                ]
            ),
        )

    def test_action_optin_status_3(self):
        important_events = [
            {
                "customer_key": self.key,
                "details": {
                    "commown": {
                        "optin_ts": _date(2019, 12, 25),
                        "optout_ts": _date(2020, 3, 1),
                    },
                    "telecoop": {"optin_ts": _date(2020, 1, 1), "optout_ts": None},
                },
                "events": [{"type": "optin", "ts": _date(2020, 1, 1)}],
            }
        ]

        self.assertEqual(
            self.optin_status(important_events),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: fully subscribed",
                    "--",
                    "Validity: 01/01/2020 00:00:00",
                    "--",
                    "Key: %s" % self.key,
                    "--",
                    "Details:",
                    "- commown: 12/25/2019 00:00:00 > 03/01/2020 00:00:00",
                    "- telecoop: 01/01/2020 00:00:00",
                ]
            ),
        )

    def test_wizard_late_optin(self):
        wizard = self.env["coupon.late.optin.wizard"].create(
            {
                "coupon_id": self.coupon.id,
            }
        )

        optin = {"customer_key": self.key, "optin_ts": _date(2020, 1, 1)}

        with requests_mock.Mocker() as rm:
            rm.post(self.paths["opt-in"], json=optin)
            wizard.late_optin()

    def test_wizard_late_optin_error(self):
        wizard = self.env["coupon.late.optin.wizard"].create(
            {
                "coupon_id": self.coupon.id,
            }
        )

        with requests_mock.Mocker() as rm:
            rm.post(
                self.paths["opt-in"],
                status_code=422,
                json={"detail": "Already opt-in"},
            )
            with self.assertRaises(UserError) as err:
                wizard.late_optin()

        self.assertEqual(
            err.exception.name,
            "Already opt-in (may not be visible if before the campaign start)",
        )
