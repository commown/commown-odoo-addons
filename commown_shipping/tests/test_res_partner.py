from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class ResPartnerTC(TransactionCase):
    @mute_logger("odoo.sql_db")
    def test_street_length_low_level(self):
        with self.assertRaises(IntegrityError) as err:
            partner = self.env["res.partner"].create({"name": "T", "street": "a" * 36})
        self.assertIn("res_partner_street_max_size_colissimo", err.exception.pgerror)

    @mute_logger("odoo.sql_db")
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
