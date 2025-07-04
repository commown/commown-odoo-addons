import coreapi
import requests_mock

import odoo.addons.payment_slimpay_dump_restore_utils.models.utils as utils

from .common import PaymentSlimpayDumpUtilsCommonTC


class PaymentSlimpayDumpUtilsTC(PaymentSlimpayDumpUtilsCommonTC):
    "This test class serves to test edge cases of dump utils methods."

    def test_replace_mandate(self):
        """
        This test covers the following two test cases from replace_mandate,
        which weren't covered in test_provider :
        - The partner being a company
        - The signatory country value being unset
        """
        test_company = self.env["res.partner"].create(
            {
                "name": "Company Test",
                "is_company": True,
            }
        )
        token = self.env["payment.token"].create(
            {
                "partner_id": test_company.id,
                "provider_id": self.env.ref("payment.payment_provider_demo").id,
                "provider_ref": "to-be-overwritten",
            }
        )
        test_company.payment_token_id = token

        mandate_repr = self.basic_mandate("TEST-COMPANY", test_company.id)
        mandate_repr["signatory"]["billingAddress"]["country"] = None

        with requests_mock.Mocker() as rm:
            self._mock_slimpay_root_doc(rm)
            self._mock_create_mandates(rm)
            utils.replace_mandate(self.slimpay, mandate_repr)

        self.assertEqual(1, self.nb_func_call(rm.request_history, "/create-mandates"))
        self.assertEqual(token.provider_ref, "new-mandate-id")
        self.assertEqual(token.provider_id, self.slimpay)

    def test_get_partner_with_token_reference(self):
        """
        We check the get_partner method, for the case where the reference is not an integer,
        but a token reference.
        """
        admin_partner = self.env.ref("base.partner_admin")
        demo_partner = self.env.ref("base.partner_demo")
        mandate_doc = coreapi.Document(
            content={
                "id": "test_id",
                "https://api.slimpay.net/alps#get-subscriber": coreapi.Link(
                    url=self.slimpay_api + "/subscriber/test-ref",
                ),
            }
        )

        token = self.env["payment.token"].create(
            {
                "partner_id": admin_partner.id,
                "provider_id": self.slimpay.id,
                "provider_ref": "test_id",
            }
        )

        # Case 1: The token isn't assigned to any partner
        with requests_mock.Mocker() as rm1:
            self._mock_slimpay_root_doc(rm1)
            no_partner = utils.get_partner(self.slimpay, mandate_doc)
        self.assertFalse(no_partner.exists())

        # Case 2: The token is assigned to 2 partners, which is the admin's
        admin_partner.payment_token_id = token
        demo_partner.payment_token_id = token

        with requests_mock.Mocker() as rm2:
            self._mock_slimpay_root_doc(rm2)
            rm2.get(
                self.slimpay_api + "/subscriber/test-ref",
                json={"reference": str(admin_partner.id)},
            )
            valid_partner = utils.get_partner(self.slimpay, mandate_doc)

            self.assertEqual(
                1, self.nb_func_call(rm2.request_history, "/subscriber/test-ref")
            )

        self.assertTrue(valid_partner.exists())
        self.assertEqual(valid_partner, admin_partner)
