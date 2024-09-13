import phonenumbers

from odoo.tests.common import SavepointCase

from ..models.common import normalize_phone


class CommonFunctionsTC(SavepointCase):
    def setUp(self):
        super(SavepointCase, self).setUp()

    def test_normalize_phone(self):
        self.assertEqual(
            normalize_phone("06 23 23.23.23", "FR", number_format="national"),
            "0623232323",
        )
        self.assertEqual(
            normalize_phone(" +337 33 22 11 00", "FR", number_format="national"),
            "0733221100",
        )
        self.assertEqual(
            normalize_phone("06 23 23.23.23", "FR"),
            "+33623232323",
        )
        self.assertEqual(normalize_phone(False, "FR"), "")

        with self.assertRaises(phonenumbers.NumberParseException) as err:
            normalize_phone("not a phone", "FR")

        self.assertEqual(normalize_phone("not a phone", "FR", raise_on_error=False), "")
