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
            "subscribed": ("/campaign/test-campaign/subscribed"),
            "subscriptions": (
                "/campaign/test-campaign/subscriptions?customer_key=%s" % self.key
            ),
        }

    def optin_status(self, subscribed, subscriptions=None):
        with requests_mock.Mocker() as rm:
            rm.get(self.paths["subscribed"], json=subscribed)
            if subscriptions is not None:
                rm.get(self.paths["subscriptions"], json=subscriptions)
            with self.assertRaises(UserError) as err:
                self.coupon.action_coop_campaign_optin_status()
        return err.exception.name.strip()

    def _test_action_optin_status_0(self):
        subscribed = {self.key: False}
        subscriptions = []

        self.assertEqual(
            self.optin_status(subscribed, subscriptions),
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

    def _test_action_optin_status_1(self):
        subscribed = {self.key: False}
        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "optin_ts": _date(2020, 1, 1),
                "optout_ts": None,
                "reason": "",
                "member": telecoop,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            }
        ]

        self.assertEqual(
            self.optin_status(subscribed, subscriptions),
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

    def _test_action_optin_status_2(self):
        subscribed = {self.key: True}
        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "optin_ts": _date(2019, 12, 25),
                "optout_ts": None,
                "reason": "",
                "member": commown,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
            {
                "customer_key": self.key,
                "optin_ts": _date(2020, 1, 1),
                "optout_ts": None,
                "reason": "",
                "member": telecoop,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
        ]

        self.assertEqual(
            self.optin_status(subscribed, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: fully subscribed",
                    "--",
                    "Subscription to commown: 12/25/2019 00:00:00",
                    "Subscription to telecoop: 01/01/2020 00:00:00",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def _test_action_optin_status_3(self):
        subscribed = {self.key: True}
        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "optin_ts": _date(2019, 12, 25),
                "optout_ts": _date(2020, 3, 1),
                "reason": "Contract 1",
                "member": commown,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
            {
                "customer_key": self.key,
                "optin_ts": _date(2020, 2, 25),
                "optout_ts": None,
                "reason": "Contract 2",
                "member": commown,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
            {
                "customer_key": self.key,
                "member": telecoop,
                "optin_ts": _date(2020, 1, 1),
                "optout_ts": None,
                "reason": "",
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
            },
        ]

        self.assertEqual(
            self.optin_status(subscribed, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: fully subscribed",
                    "--",
                    (
                        "Subscription to commown:"
                        " 12/25/2019 00:00:00 > 03/01/2020 00:00:00 (Contract 1)"
                    ),
                    "Subscription to commown: 02/25/2020 00:00:00 (Contract 2)",
                    "Subscription to telecoop: 01/01/2020 00:00:00",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def _test_action_optin_status_4(self):
        subscribed = {self.key: False}
        telecoop = {"login": "telecoop", "id": 1}
        commown = {"login": "commown", "id": 2}
        subscriptions = [
            {
                "customer_key": self.key,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
                "member": commown,
                "reason": "",
                "optin_ts": _date(2021, 12, 31),
                "optout_ts": _date(2022, 4, 21),
            },
            {
                "customer_key": self.key,
                "campaign": {"ref": "telecommown", "members": [telecoop, commown]},
                "member": telecoop,
                "reason": "",
                "optin_ts": _date(2021, 10, 28),
                "optout_ts": None,
            },
        ]

        self.assertEqual(
            self.optin_status(subscribed, subscriptions),
            "\n".join(
                [
                    "Subscription status for Joel Willis is: not fully subscribed",
                    "--",
                    "Subscription to commown: 12/31/2021 00:00:00 > 04/21/2022 00:00:00",
                    "Subscription to telecoop: 10/28/2021 00:00:00",
                    "--",
                    "Key: %s" % self.key,
                ]
            ),
        )

    def test_wizard_late_optin(self):
        action = self.coupon.action_coop_campaign_optin_now()
        self.assertEqual(action["res_model"], "coupon.late.optin.wizard")
        self.assertEqual(action["context"]["default_coupon_id"], self.coupon.id)

        wizard = self.env["coupon.late.optin.wizard"].create(
            {"coupon_id": self.coupon.id}
        )
        wizard._onchange_coupon_id()
        self.assertTrue(wizard.contract_id)

        optin = {"customer_key": self.key, "optin_ts": _date(2020, 1, 1)}

        with requests_mock.Mocker() as rm:
            rm.post(self.paths["opt-in"], json=optin)
            wizard.late_optin()

    def _test_wizard_late_optin_error(self):
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
