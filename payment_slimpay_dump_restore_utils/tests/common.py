from odoo.tests.common import TransactionCase


class PaymentSlimpayDumpUtilsCommonTC(TransactionCase):
    "This class sets up mocks for the Slimpay requests used in the utils"

    def setUp(self):
        self.dummy_sign_date = "2025-01-01T23:59:59.000+0000"
        super().setUp()
        self.slimpay = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        self.slimpay_api = self.slimpay.slimpay_api_url

    # Request mock setup helpers
    def _mock_slimpay_root_doc(self, mocker):
        "Mock all necessary slimpay requests to get a client and a basic root doc"

        mocker.post(self.slimpay_api + "/oauth/token", json={"access_token": "mytoken"})
        mocker.get(
            self.slimpay_api + "/",
            json={
                "_links": {
                    "https://api.slimpay.net/alps#search-mandates": {
                        "href": "/search-mandates",
                    },
                    "https://api.slimpay.net/alps#create-mandates": {
                        "href": "/create-mandates",
                    },
                },
            },
        )

    def _mock_get_bank_account(self, mocker):
        mocker.get(
            self.slimpay_api + "/get-bank-account",
            json={"bic": "ABCDEFGH", "iban": "FR00"},
        )

    def _mock_search_mandates(self, mocker, pagination=True):
        """
        Mock the GET search-mandates endpoint.
        The pagination argument allows to create another page of mandates.
        """
        search_mandates_json = {
            "_embedded": {
                "mandates": self.mandates_list(),
                "page": {"size": 1, "totalPages": 1},
            }
        }

        if pagination:
            search_mandates_json.update(
                {
                    "page": {"size": 2, "totalPages": 2},
                    "_links": {
                        "next": {"href": self.slimpay_api + "/mandates?page=2"},
                    },
                }
            )
            mocker.get(
                self.slimpay_api + "/mandates",
                json={"_embedded": {"mandates": self.mandates_list()}},
            )

        mocker.get(self.slimpay_api + "/search-mandates", json=search_mandates_json)

    def _mock_create_mandates(self, mocker):
        mocker.post(
            self.slimpay_api + "/create-mandates",
            json={
                "dateSigned": self.dummy_sign_date,
                "id": "new-mandate-id",
                "reference": "CREATED-MANDATE",
            },
        )

    def nb_func_call(self, request_history, func):
        return len([req for req in request_history if func in req.url])

    # Mandates dicts helpers
    def mandates_list(self):
        return [
            {
                "reference": "TEST-GET",
                "id": "001",
                "dateSigned": self.dummy_sign_date,
                "_links": {
                    "https://api.slimpay.net/alps#get-subscriber": {
                        "href": "https://api.local/creditors/democreditor/subscribers/3",
                    },
                    "https://api.slimpay.net/alps#get-bank-account": {
                        "href": self.slimpay_api + "/get-bank-account"
                    },
                },
            },
            {
                "reference": "NEVER-VALID",
                "id": "001",
                "dateSigned": self.dummy_sign_date,
                "_links": {
                    "https://api.slimpay.net/alps#get-subscriber": {
                        "href": "https://api.local/creditors/democreditor/subscribers/0",
                    },  # With the partner id set to 0, this will never render a mandate.
                    "https://api.slimpay.net/alps#get-bank-account": {
                        "href": self.slimpay_api + "/get-bank-account"
                    },
                },
            },
        ]

    def basic_mandate(self, reference, subscriber_ref):
        return {
            "reference": reference,
            "subscriber": {"reference": subscriber_ref},
            "signatory": {
                "givenName": "Foo",
                "familyName": "Bar",
                "email": "test@test.coop",
                "billingAddress": {
                    "street1": "1 Rue du Boulevard",
                    "postalCode": "12345",
                    "city": "Villebourg",
                    "country": "FR",
                },
                "bankAccount": {
                    "bic": "ABCDEFGH",
                    "iban": "FR00",
                },
            },
        }
