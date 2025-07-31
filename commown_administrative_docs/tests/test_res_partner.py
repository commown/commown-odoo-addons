from base64 import b64encode
from pathlib import Path

import magic

from odoo.tests import TransactionCase

HERE = (Path(__file__) / "..").resolve()


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

    def test_image(self):
        "Images should be parsed correctly"
        self.assertFalse(self.partner.id_card1)
        with open(HERE / "smallest.jpg", "rb") as fobj:
            img = fobj.read()
            self.assertIn("image", magic.from_buffer(img, mime=True))
            self.partner.id_card1 = b64encode(img)

        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.id_card1)
