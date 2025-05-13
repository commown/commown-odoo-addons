import requests_mock
from mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_payment_slimpay.models import slimpay_utils


@tagged("-at_install", "post_install")
class SlimpayUtilsTC(TransactionCase):
    def setUp(self):
        super().setUp()
        france = self.env["res.country"].search([("code", "=", "FR")])
        self.partner = self.env["res.partner"].create(
            {"firstname": "F", "lastname": "C/@\\é9", "country_id": france.id}
        )

    def check_phone_value(self, expected):
        actual = slimpay_utils.partner_mobile_phone(self.partner)
        if expected is None:
            self.assertIsNone(actual)
        else:
            self.assertEqual(expected, actual)

    def test_slimpay_mobile_phone(self):
        self.partner.write({"phone": None})
        self.check_phone_value(None)
        self.partner.write({"phone": "06.01.02.03.04"})
        self.check_phone_value("+33601020304")
        self.partner.write({"phone": "invalid!"})
        self.check_phone_value(None)
        self.partner.write({"phone": "+33 1 02 03 04 05"})
        self.check_phone_value(None)

    def test_slimpay_signatory(self):
        subscriber = slimpay_utils.subscriber_from_partner(self.partner)
        self.assertEqual(
            {
                "familyName": "Cé",
                "email": None,
                "givenName": "F",
                "telephone": None,
                "billingAddress": {
                    "city": None,
                    "country": "FR",
                    "postalCode": None,
                    "street1": None,
                    "street2": None,
                },
            },
            subscriber["signatory"],
        )
        self.assertEqual(self.partner.id, subscriber["reference"])

        self.partner.write(
            {
                "street": "2 rue de Rome",
                "street2": "Appt X",
                "zip": "67000",
                "city": "Strasbourg",
            }
        )
        subscriber = slimpay_utils.subscriber_from_partner(self.partner)
        self.assertEqual(self.partner.id, subscriber["reference"])
        self.assertEqual(
            {
                "familyName": "Cé",
                "email": None,
                "givenName": "F",
                "telephone": None,
                "billingAddress": {
                    "city": "Strasbourg",
                    "country": "FR",
                    "postalCode": "67000",
                    "street1": "2 rue de Rome",
                    "street2": "Appt X",
                },
            },
            subscriber["signatory"],
        )

    def test_slimpay_api_create_order(self):
        euro = self.env.ref("base.EUR")
        with patch.object(slimpay_utils, "get_client"):
            client = slimpay_utils.SlimpayClient(
                "api_url", "creditor", "app_id", "app_secret"
            )
        subscriber = slimpay_utils.subscriber_from_partner(self.partner)
        result = client._repr_order(
            "tx",
            "so",
            "fr",
            149.20000000000002,
            euro.name,
            euro.decimal_places,
            subscriber,
            "https://commown.fr/",
        )
        self.assertEqual("tx", result["reference"])
        self.assertEqual("fr", result["locale"])
        self.assertEqual(
            ["signMandate", "payment"], [item["type"] for item in result["items"]]
        )
        sign, payment = result["items"]
        self.assertIn("signatory", sign["mandate"])
        self.assertEqual(149.20, payment["payin"]["amount"])
        self.assertEqual("so", payment["payin"]["label"])
        self.assertEqual("EUR", payment["payin"]["currency"])

    def test_get_client(self):
        with requests_mock.Mocker() as rm:
            rm.post("https://api.local/oauth/token", json={"access_token": "mytoken"})
            client = slimpay_utils.get_client(
                "https://api.local", "myappid", "myappsecret"
            )

        self.assertEqual(len(rm.request_history), 1)
        req = rm.request_history[0]
        self.assertEqual(
            req.headers["Authorization"], "Basic bXlhcHBpZDpteWFwcHNlY3JldA=="
        )

        self.assertEqual(
            client.transports[0].headers["authorization"], "Bearer mytoken"
        )

    def test_approval_url(self):
        subscriber = slimpay_utils.subscriber_from_partner(self.partner)

        with patch.object(slimpay_utils, "get_client") as mock:
            client = slimpay_utils.SlimpayClient(
                "api_url", "creditor", "app_id", "app_secret"
            )

        client.approval_url(
            "tx_ref", "mylabel", "fr", 20.10, "EUR", 2, subscriber, "http://return.url"
        )

        def get_mock_call(name):
            for call in mock.mock_calls:  # pragma: no branch
                if str(call).startswith("call().%s(" % name):
                    return call

        action_mc = get_mock_call("action")
        self.assertEqual(
            action_mc.args[1],
            "https://api.slimpay.net/alps#create-orders",
        )
        self.assertEqual(list(action_mc.kwargs), ["action", "validate", "params"])
        self.assertEqual(action_mc.kwargs["action"], "POST")
        self.assertEqual(action_mc.kwargs["params"]["reference"], "tx_ref")
        self.assertEqual(action_mc.kwargs["params"]["returnUrl"], "http://return.url")
        self.assertEqual(action_mc.kwargs["params"]["items"][0]["type"], "signMandate")
        self.assertEqual(action_mc.kwargs["params"]["items"][1]["type"], "payment")
        self.assertEqual(
            action_mc.kwargs["params"]["items"][1]["payin"],
            {
                "scheme": "SEPA.DIRECT_DEBIT.CORE",
                "direction": "IN",
                "amount": 20.1,
                "currency": "EUR",
                "label": "mylabel",
            },
        )

    def test_last_valid_mandate(self):
        api_url = "https://api.local"
        _url = "https://api.slimpay.net"
        root_doc = {
            "_links": {
                _url
                + "/alps#search-mandates": {
                    "href": _url + "/mandates{?creditorReference,subscriberReference}",
                    "templated": True,
                },
            }
        }
        mandates_doc = {
            "mandates": [
                {"id": "m1", "state": "active", "dateSigned": "2025-01-01T09:00:00"},
                {"id": "m2", "state": "inactive", "dateSigned": "2025-02-01T09:00:00"},
                {"id": "m3", "state": "active", "dateSigned": "2025-01-15T09:00:00"},
            ]
        }

        with requests_mock.Mocker() as rm:
            rm.post(api_url + "/oauth/token", json={"access_token": "mytoken"})
            client = slimpay_utils.SlimpayClient(api_url, "cred", "app", "secret")

            rm.get(api_url + "/", json=root_doc)
            rm.get(
                _url + "/mandates?creditorReference=cred&subscriberReference=mysubref",
                json=mandates_doc,
            )
            result = client.last_valid_mandate("mysubref")

        self.assertEqual(result["id"], "m3")
