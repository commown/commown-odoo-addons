from datetime import date

import requests_mock
from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


def _date(year, month, day):
    return date(year, month, day).isoformat()


class CouponTestTC(TransactionCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.campaign = cls.env["coupon.campaign"].create(
            {
                "name": "test-campaign",
                "seller_id": 1,
                "is_coop_campaign": True,
                "cooperative_salt": "no matter",
            }
        )
        so = cls.env.ref("sale.portal_sale_order_1")
        cls.coupon = cls.env["coupon.coupon"].create(
            {
                "code": "TEST",
                "campaign_id": cls.campaign.id,
                "used_for_sale_id": so.id,
            }
        )
        cls.partner = cls.coupon.used_for_sale_id.partner_id
        cls.partner.update(
            {
                "country_id": cls.env.ref("base.fr").id,
                "mobile": "0601020304",
            }
        )
        cls.key = cls.campaign.coop_partner_identifier(so.partner_id)
        cls.paths = {
            "opt-in": "/campaigns/test-campaign/opt-in",
            "important-events": (
                "/campaigns/test-campaign/subscriptions" "/important-events"
            ),
            "subscriptions": (
                "/campaign/test-campaign/" "subscriptions?customer_key=%s" % cls.key
            ),
        }

    def optin_status(self, important_events, subscriptions=None):
        with requests_mock.Mocker() as rm:
            rm.get(self.paths["important-events"], json=important_events)
            if subscriptions is not None:
                rm.get(self.paths["subscriptions"], json=subscriptions)
            with self.assertRaises(UserError) as err:
                self.coupon.action_coop_campaign_optin_status()
        return err.exception.args[0].strip()

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

    def _data_with_unsubscription(self):
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
                "events": [
                    {"type": "optin", "ts": _date(2020, 1, 1)},
                    {"type": "optout", "ts": _date(2020, 3, 1)},
                ],
            }
        ]

        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "optin_ts": _date(2019, 12, 25),
                "optout_ts": _date(2020, 3, 1),
                "member": commown,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
            {
                "customer_key": self.key,
                "optin_ts": _date(2020, 1, 1),
                "optout_ts": None,
                "member": telecoop,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
        ]

        return important_events, subscriptions

    def test_action_optin_status_with_future_unsubscription(self):
        important_events, _subscriptions = self._data_with_unsubscription()

        with freeze_time("2020-02-25"):
            self.assertEqual(
                self.optin_status(important_events),  # no http call to subscriptions
                "\n".join(
                    [
                        "Subscription status for Joel Willis is: fully subscribed",
                        "--",
                        "Validity: 01/01/2020 00:00:00 >> 03/01/2020 00:00:00",
                        "--",
                        "Key: %s" % self.key,
                        "--",
                        "Details:",
                        "- commown: 12/25/2019 00:00:00 > 03/01/2020 00:00:00",
                        "- telecoop: 01/01/2020 00:00:00",
                    ]
                ),
            )

    def test_action_optin_status_with_passed_unsubscription(self):
        important_events, subscriptions = self._data_with_unsubscription()

        self.assertEqual(
            self.optin_status(important_events, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: not fully subscribed",
                    "--",
                    "Subscription to commown: 12/25/2019 00:00:00 > 03/01/2020 00:00:00",
                    "Subscription to telecoop: 01/01/2020 00:00:00",
                    "No subscription to telecoop.",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def test_prerequisites_error_not_cooperative_campaign(self):
        self.coupon.campaign_id.is_coop_campaign = False

        with self.assertRaises(UserError) as err:
            self.coupon.action_coop_campaign_optin_status()

        self.assertEqual(err.exception.args[0], "Not a cooperative campaign!")

    def test_prerequisites_error_no_partner_key(self):
        self.coupon.used_for_sale_id.partner_id.country_id = False

        with self.assertRaises(UserError) as err:
            self.coupon.action_coop_campaign_optin_status()

        self.assertEqual(
            err.exception.args[0],
            "Partner (Joel Willis) has no valid key.",
        )

    def test_action_optin_now(self):
        result = self.coupon.action_coop_campaign_optin_now()

        self.assertEqual(result["src_model"], "coupon.coupon")
        self.assertEqual(result["res_model"], "coupon.late.optin.wizard")
        self.assertEqual(result["context"].get("default_coupon_id"), self.coupon.id)

    def test_coop_partner_identifier_ok(self):
        self.assertEqual(
            self.campaign.coop_partner_identifier(self.partner),
            "04ca4c637f7445ab54673d8923a95f847a2c97f8a52ed2c8bd2b5381f666bfb7",
        )

    def test_coop_partner_identifier_error_not_cooperative_campaign(self):
        self.campaign.is_coop_campaign = False
        self.assertIsNone(self.campaign.coop_partner_identifier(self.partner))

    def test_coop_partner_identifier_error_no_country(self):
        self.partner.country_id = False
        self.assertIsNone(self.campaign.coop_partner_identifier(self.partner))

    def test_coop_partner_identifier_error_no_mobile(self):
        self.partner.update({"mobile": False, "phone": "0352535455"})
        self.assertIsNone(self.campaign.coop_partner_identifier(self.partner))

    def test_coop_partner_identifier_error_no_salt(self):
        self.campaign.cooperative_salt = False

        chan = "odoo.addons.commown_cooperative_campaign.models.coupon"
        with self.assertLogs(chan, level="ERROR") as cm:
            self.assertIsNone(self.campaign.coop_partner_identifier(self.partner))

        self.assertEqual(
            cm.output,
            [f"ERROR:{chan}:Cooperative campaign {self.campaign.id} has no salt set"],
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
            err.exception.args[0],
            "Already opt-in (may not be visible if before the campaign start)",
        )
