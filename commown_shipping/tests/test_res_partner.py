from contextlib import contextmanager

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase

from ..models.colissimo_utils import ColissimoError


class ResPartnerTC(TransactionCase):
    "Tests for partner methods implemented in present module"

    def test_street_length_low_level(self):
        with self.assertRaises(IntegrityError) as err:
            partner = self.env["res.partner"].create({"name": "T", "street": "a" * 36})
        self.assertIn("res_partner_street_max_size_colissimo", err.exception.pgerror)

    def test_street2_length_low_level(self):
        with self.assertRaises(IntegrityError) as err:
            partner = self.env["res.partner"].create({"name": "T", "street2": "a" * 36})
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

    def test_colissimo_delivery_data(self):
        @contextmanager
        def emptied_fields(partner, *fields):
            old_values = {}
            for field in fields:
                old_values[field] = getattr(partner, field)
                setattr(partner, field, False)
            yield
            for field in fields:
                setattr(partner, field, old_values[field])

        partner = self.env["res.partner"].create(
            {
                "firstname": "Firsttest",
                "lastname": "Lasttest",
                "street": "8A rue Schertz",
                "zip": "67200",
                "city": "Strasbourg",
                "country_id": self.env.ref("base.fr").id,
                "mobile": "060101010101",
                "phone": "030101010101",
                "email": "contact@commown.coop",
            }
        )

        expected = {
            "city": "Strasbourg",
            "countryCode": "FR",
            "email": "contact@commown.coop",
            "firstName": "Firsttest",
            "lastName": "Lasttest",
            "line2": "8A rue Schertz",
            "mobileNumber": "60101010101",
            "phoneNumber": "30101010101",
            "zipCode": "67200",
        }
        self.assertEqual(partner.colissimo_delivery_data(), expected)

        # Email is mandatory...
        with emptied_fields(partner, "email"):
            with self.assertRaises(ColissimoError) as err:
                partner.colissimo_delivery_data()
        self.assertEqual(
            err.exception.args, ("An email is required to generate a Colissimo label!",)
        )

        # ... and one phone number at least is mandatory...
        with emptied_fields(partner, "phone", "mobile"):
            with self.assertRaises(ColissimoError) as err:
                partner.colissimo_delivery_data()
        self.assertEqual(
            err.exception.args,
            ("A phone number is required to generate a Colissimo label!",),
        )

        # ... unless asked to not raise
        new_expected = expected.copy()
        new_expected.update({"email": "", "mobileNumber": "", "phoneNumber": ""})
        with emptied_fields(partner, "email", "phone", "mobile"):
            self.assertEqual(
                partner.colissimo_delivery_data(raise_on_error=False),
                new_expected,
            )
