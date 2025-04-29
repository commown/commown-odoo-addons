from base64 import decodebytes
from datetime import date
from io import BytesIO

from odf import opendocument
from odf.table import Table, TableCell, TableRow

from .common import TestShareholderRegisterTC


class TestShareholderRegister(TestShareholderRegisterTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_move_lines = cls.env["account.move.line"]
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 3, 12), 2000)
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 8, 12), -2000)
        cls._add_shares(cls.partner_2, cls.account_beneficiaire, (2018, 3, 12), 100)
        cls._add_shares(cls.partner_2, cls.account_soutien, (2018, 3, 12), 200)
        cls._add_shares(cls.partner_2, cls.account_porteur, (2018, 3, 12), 20)
        cls._add_shares(cls.partner_3, cls.account_soutien, (2018, 3, 12), -200)

    def register(self, *date_tuple):
        reg = self.env["commown_shareholder_register.register"].create(
            {"date": date(*date_tuple)}
        )
        return reg

    def test_get_shareholders(self):

        result = self.register(2018, 7, 24).get_shareholders()
        # Check total balance
        self.assertEqual(result["total"]["balance"], 2300)
        # Check college assignation
        self.assertEqual(result["partners"][self.partner_2]["college"].name, "D")
        # Check college balance calculation
        self.assertEqual(result["colleges"][self.college_A]["total"], 2000)
        self.assertEqual(result["colleges"][self.college_D]["total"], 300)
        # Check that the partner with no more shares is not in the register
        result = self.register(2018, 8, 13).get_shareholders()
        self.assertFalse(self.partner_1 in result["partners"])

        self.assertCountEqual(
            result["warnings"],
            [
                "The partner Partner 2 has not enough shares for college A",
                "The partner Partner 3 has a negative share number",
            ],
        )

    def test_report(self):
        # Beware that the row index depends on the number of colleges
        sheet_idx, row_idx, col_idx = 0, 6, 2
        register = self.register(2018, 8, 13)
        reg_data = register.get_shareholders()
        register.generate_register()
        ods_file = opendocument.load(BytesIO(decodebytes(register.report)))
        value = (
            ods_file.getElementsByType(Table)[sheet_idx]
            .getElementsByType(TableRow)[row_idx]
            .getElementsByType(TableCell)[col_idx]
            .getAttribute("value")
        )
        self.assertEqual(float(value), reg_data["total"]["balance"])
