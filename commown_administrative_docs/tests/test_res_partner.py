from odoo.tests import TransactionCase


class AdminDocsPartnerTC(TransactionCase):
    "This class serves to test the res.partner methods with more granularity"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.partner_demo")

    def test_invalid_filetype_passed(self):
        "Valid formats should only be strings and bytes"
        with self.assertRaises(ValueError) as err:
            self.partner.id_card1 = 1

        self.assertIn("is not covered by this function", err.exception.args[0])
