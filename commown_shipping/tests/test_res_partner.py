import phonenumbers
from psycopg2 import IntegrityError

from odoo.tests.common import SavepointCase
from odoo.tools import mute_logger

from ..models.colissimo_utils import ColissimoError


class ResPartnerContraintsTC(SavepointCase):
    "Tests for partner SQL contraints of present module"

    def test_street_length_low_level(self):
        with self.assertRaises(IntegrityError) as err:
            with mute_logger("odoo.sql_db"):
                partner = self.env["res.partner"].create(
                    {"name": "T", "street": "a" * 36}
                )
        self.assertIn("res_partner_street_max_size_colissimo", err.exception.pgerror)

    def test_street2_length_low_level(self):
        with self.assertRaises(IntegrityError) as err:
            with mute_logger("odoo.sql_db"):
                partner = self.env["res.partner"].create(
                    {"name": "T", "street2": "a" * 36}
                )
        self.assertIn("res_partner_street2_max_size_colissimo", err.exception.pgerror)

    def test_street_validation(self):
        errors, messages = {}, []
        self.env["res.partner"].validate_street_lines(
            {"name": "T", "street": "a" * 36, "street2": "b" * 36},
            errors,
            messages,
        )

        self.assertEqual(errors.get("street"), "error")
        self.assertEqual(errors.get("street2"), "error")
        self.assertEqual(
            messages,
            ["Address lines' length is limited to 35. Please fix."],
        )


class ResPartnerColissimoDeliveryDataTC(SavepointCase):
    "Test of the colissimo_delivery_data method"

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "firstname": "Firsttest",
                "lastname": "Lasttest",
                "street": "8A rue Schertz",
                "zip": "67200",
                "city": "Strasbourg",
                "country_id": self.env.ref("base.fr").id,
                "email": "contact@commown.coop",
                "mobile": "0652535455",
                "phone": "0352535455",
            }
        )
        self.expected = {
            "city": "Strasbourg",
            "countryCode": "FR",
            "email": "contact@commown.coop",
            "firstName": "Firsttest",
            "lastName": "Lasttest",
            "line2": "8A rue Schertz",
            "mobileNumber": "0652535455",
            "phoneNumber": "0352535455",
            "zipCode": "67200",
        }

    def test_ok(self):
        self.assertEqual(self.partner.colissimo_delivery_data(), self.expected)

    def test_b2c_delivery(self):
        partner = self.partner.copy({"email": "a@b.coop", "parent_id": self.partner.id})
        partner.lastname = "Lasttest"  # Avoid automatic 'copy' suffix

        expected = dict(self.expected, email="a@b.coop")
        self.assertEqual(partner.colissimo_delivery_data(), expected)

    def test_b2b_delivery(self):
        company = self.partner.copy({"is_company": True, "name": "Test Company"})
        self.partner.parent_id = company.id
        partner = self.partner.copy({"type": "delivery", "parent_id": self.partner.id})
        partner.lastname = "Lasttest"  # Avoid automatic 'copy' suffix

        expected = dict(self.expected, companyName="Test Company")
        self.assertEqual(partner.colissimo_delivery_data(), expected)

    def test_phone_mobile_in_fixed(self):
        "Output correct partner's mobile even when it is in the fixed phone field"

        self.partner.phone = self.partner.mobile
        self.partner.mobile = False

        expected = dict(self.expected, phoneNumber="")
        self.assertEqual(self.partner.colissimo_delivery_data(), expected)

    def _check_invalid_phone(self):
        expected_msg = "The string supplied did not seem to be a phone number."
        with self.assertRaises(phonenumbers.NumberParseException) as err:
            self.partner.colissimo_delivery_data()
        self.assertEqual(err.exception.args, (expected_msg,))

    def test_invalid_fixed_raise(self):
        "Colissimo data method  should raise when the fixed phone number is invalid"

        self.partner.phone = "invalid!"
        self._check_invalid_phone()

    def test_invalid_fixed_no_raise(self):
        "When asked not to raise an invalid fixed phone value must result in ''"

        self.partner.phone = "invalid!"
        self.assertEqual(
            self.partner.colissimo_delivery_data(raise_on_error=False),
            dict(self.expected, phoneNumber=""),
        )

    def test_invalid_mobile_raise(self):
        "Colissimo data method should raise when the mobile phone number is invalid"

        self.partner.mobile = "invalid!"
        self._check_invalid_phone()

    def test_invalid_mobile_no_raise(self):
        "When asked not to raise an invalid mobile phone value must result in ''"

        self.partner.mobile = "invalid!"
        self.assertEqual(
            self.partner.colissimo_delivery_data(raise_on_error=False),
            dict(self.expected, mobileNumber=""),
        )

    def test_one_mandatory_phone_raise(self):
        "At least one phone number is mandatory for colissimo delivery"

        # Check with only one phone number: must not crash
        phone = self.partner.phone
        self.partner.update({"phone": False})
        self.partner.colissimo_delivery_data()
        self.partner.update({"phone": phone, "mobile": False})
        self.partner.colissimo_delivery_data()

        # Check with no phone number: must crash
        self.partner.update({"phone": False, "mobile": False})
        with self.assertRaises(ColissimoError) as err:
            self.partner.colissimo_delivery_data()
        self.assertEqual(
            err.exception.args,
            ("A phone number is required to generate a Colissimo label!",),
        )

    def test_mandatory_email_raise(self):
        "Email is mandatory for colissimo delivery"

        self.partner.email = False
        expected_msg = "An email is required to generate a Colissimo label!"

        with self.assertRaises(ColissimoError) as err:
            self.partner.colissimo_delivery_data()
        self.assertEqual(err.exception.args, (expected_msg,))

    def test_mandatory_email_no_raise(self):
        "When asked not to raise no email must result in an empty str in colissimo data"

        self.partner.email = False
        self.assertEqual(
            self.partner.colissimo_delivery_data(raise_on_error=False),
            dict(self.expected, email=""),
        )
