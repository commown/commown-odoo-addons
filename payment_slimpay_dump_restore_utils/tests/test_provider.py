import json
import os
import tempfile

import requests_mock

from odoo.addons.account_payment_slimpay.models import slimpay_utils

from .common import PaymentSlimpayDumpUtilsCommonTC


class SlimpayDumpProviderUtilsTC(PaymentSlimpayDumpUtilsCommonTC):
    "This class serves to test the model methods related to this model"

    def setUp(self):
        super().setUp()
        self.dump_file = tempfile.NamedTemporaryFile(delete=False)

    def tearDown(self):
        super().tearDown()
        self.dump_file.close()
        os.unlink(self.dump_file.name)

    # Tests
    def test_dump_and_restore(self):
        """
        We check if the dumped mandates are valid to restore w/out crashing.
        We also define the Slimpay provider, for coverage purposes.
        """

        # Data initialisation - To be able to create a mandate,
        # the returned user (admin_partner) needs to have a valid contract.
        admin_partner = self.env.ref("base.partner_admin")
        self.env["contract.contract"].create(
            {"name": "Test contract", "partner_id": admin_partner.id}
        )

        # Phase 1: We dump the database mandates.
        with requests_mock.Mocker() as rm:
            self._mock_slimpay_root_doc(rm)
            self._mock_get_bank_account(rm)
            self._mock_search_mandates(rm)
            self.env["payment.provider"]._slimpay_dump_all_mandates(
                provider=self.slimpay,
                refresh=False,
                mandates_fpath=self.dump_file.name,
            )

            self.assertEqual(
                1, self.nb_func_call(rm.request_history, "/search-mandates")
            )
            self.assertEqual(
                1, self.nb_func_call(rm.request_history, "/mandates?page=2")
            )

        with open(self.dump_file.name) as f:
            mandates = json.load(f)
            self.assertEqual(len(mandates), 2)

        # Phase 2: we restore the dumped mandates.
        # For the sake of testing, we declare another search-mandate mock.
        with requests_mock.Mocker() as rm:
            self._mock_slimpay_root_doc(rm)
            self._mock_create_mandates(rm)
            rm.get(
                self.slimpay_api + "/search-mandates",
                json={
                    "_embedded": {
                        "mandates": [
                            {
                                "reference": "DUMMY",
                                "id": "dummy",
                            }
                        ]
                    },
                    "page": {"size": 0, "totalPages": 0},
                },
            )

            self.env["payment.provider"]._slimpay_restore_mandates(
                provider=self.slimpay,
                mandates_fpath=self.dump_file.name,
            )
            # /create-mandates is only called one time,
            # because the two dumped mandates are the same
            self.assertEqual(
                1, self.nb_func_call(rm.request_history, "/create-mandates")
            )

    def test_refresh_dump(self):
        """
        We check the refresh feature, which concatenates the new mandates
        next to the old ones in an existing file.
        """

        # Data initialization
        # Since the returned mandate is based on the admin partner, we reconstitute the mandate data.
        admin_partner = self.env.ref("base.partner_admin")
        admin_partner_mandate = {
            "reference": "TEST-GET",
            "dateSigned": self.dummy_sign_date,
            "createSequenceType": "FRST",
            "subscriber": {"reference": admin_partner.id},
            "signatory": {
                "familyName": admin_partner.lastname,
                "givenName": admin_partner.firstname,
                "telephone": slimpay_utils.partner_mobile_phone(admin_partner),
                "email": admin_partner.email,
                "billingAddress": {
                    "street1": admin_partner.street,
                    "street2": admin_partner.street2 or None,
                    "postalCode": admin_partner.zip,
                    "city": admin_partner.city,
                    "country": admin_partner.country_code,
                },
                "bankAccount": {"bic": "ABCDEFGH", "iban": "FR00"},
            },
        }

        init_mandate = self.basic_mandate("TEST-REFRESH", admin_partner.id)
        init_mandate["dateSigned"] = "2024-01-01T23:59:59.000+0000"
        json.dump([init_mandate], open(self.dump_file.name, "w"))

        with requests_mock.Mocker() as rm2:
            self._mock_slimpay_root_doc(rm2)
            self._mock_get_bank_account(rm2)
            self._mock_search_mandates(rm2, pagination=False)
            self.env["payment.provider"]._slimpay_dump_all_mandates(
                mandates_fpath=self.dump_file.name
            )

            self.assertEqual(
                1, self.nb_func_call(rm2.request_history, "/search-mandates")
            )

        with open(self.dump_file.name) as f:
            mandates = json.load(f)
            self.assertEqual(len(mandates), 2)
            self.assertEqual(mandates, [init_mandate, admin_partner_mandate])

    def test_restore_various_cases(self):
        """
        We check various valid and invalid mandates cases, to run through the different
        branches of the restore_all_missing_mandates function.
        """
        admin_partner = self.env.ref("base.partner_admin")
        demo_partner = self.env.ref("base.partner_demo")

        json.dump(
            [
                self.basic_mandate("TEST-NOPARTNER", 0),
                self.basic_mandate("TEST-NOCONTRACT", demo_partner.id),
                self.basic_mandate("TEST-VALID", admin_partner.id),
                self.basic_mandate("TEST-VALID-SAME", admin_partner.id),
                self.basic_mandate("TEST-VALID-SAME", admin_partner.id),
            ],
            open(self.dump_file.name, "w"),
        )
        self.env["contract.contract"].create(
            {
                "name": "Test contract",
                "partner_id": admin_partner.id,
            }
        )

        with requests_mock.Mocker() as rm:
            self._mock_slimpay_root_doc(rm)
            self._mock_search_mandates(rm)
            self._mock_create_mandates(rm)

            self.env["payment.provider"]._slimpay_restore_mandates(
                mandates_fpath=self.dump_file.name
            )

            # create-mandates should only have been called two times,
            # because there are only 3 valid mandates, and only two of them are processed,
            # since the third one is a clone of the second one, with the same reference.
            self.assertEqual(
                2, self.nb_func_call(rm.request_history, "/create-mandates")
            )
