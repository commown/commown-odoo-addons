from base64 import decodebytes
from datetime import date
from io import BytesIO

from odf import opendocument
from odf.table import Table, TableCell, TableRow

from odoo.tests import common


class TestShareholderRegister(common.SavepointCase):
    @classmethod
    def _create_account(cls, code, name):
        account = cls.env["account.account"].create(
            {
                "name": name,
                "code": code,
                "user_type_id": cls.acc_type.id,
            }
        )
        return account

    @classmethod
    def _add_shares(cls, partner, account, date_tuple, amount):
        journal = (
            cls.env["account.journal"]
            .search([("type", "=", "general")], limit=1)
            .ensure_one()
        )
        move = cls.env["account.move"].create(
            {
                "name": "Test Account Move",
                "journal_id": journal.id,
                "date": date(*date_tuple),
            }
        )
        if amount < 0:
            attr2, attr1 = "credit", "debit"
        else:
            attr1, attr2 = "credit", "debit"

        cls.account_move_lines |= cls.env["account.move.line"].create(
            [
                {
                    "move_id": move.id,
                    "account_id": account.id,
                    "partner_id": partner.id,
                    "date": date(*date_tuple),
                    attr1: abs(amount),
                },
                {
                    "move_id": move.id,
                    "account_id": cls.account_balancing.id,
                    "partner_id": partner.id,
                    "date": date(*date_tuple),
                    attr2: abs(amount),
                },
            ]
        )

    @classmethod
    def setUpClass(cls):

        super(TestShareholderRegister, cls).setUpClass()
        cls.partner_1 = cls.env["res.partner"].create({"name": "Partner 1"})
        cls.partner_2 = cls.env["res.partner"].create({"name": "Partner 2"})
        cls.partner_3 = cls.env["res.partner"].create({"name": "Partner 3"})

        cls.acc_type = cls.env["account.account.type"].create(
            {"name": "Test", "type": "other"}
        )
        cls.account_porteur = cls._create_account("10134000", "Porteur de Projet")
        cls.account_soutient = cls._create_account("10136000", "Account Soutient")
        cls.account_beneficiaire = cls._create_account(
            "10135000", "Account Bénéficiaire"
        )
        cls.account_balancing = cls._create_account("XXXXXXXX", "Balancing journal")

        cls.account_move_lines = cls.env["account.move.line"]
        cls._add_shares(cls.partner_1, cls.account_porteur, (2022, 3, 12), 2000)
        cls._add_shares(cls.partner_1, cls.account_porteur, (2022, 8, 12), -2000)
        cls._add_shares(cls.partner_2, cls.account_beneficiaire, (2022, 3, 12), 100)
        cls._add_shares(cls.partner_2, cls.account_soutient, (2022, 3, 12), 200)
        cls._add_shares(cls.partner_2, cls.account_porteur, (2022, 3, 12), 20)
        cls._add_shares(cls.partner_3, cls.account_soutient, (2022, 3, 12), -200)

    def register(self, *date_tuple):
        reg = self.env["commown_shareholder_register.register"].create(
            {"date": date(*date_tuple)}
        )
        return reg

    def test_get_shareholders(self):
        result = self.register(2022, 7, 24).get_shareholders()
        # Check total balance
        self.assertEqual(result["total"]["balance"], 2300)
        # Check college assignation
        self.assertEqual(result["partners"][self.partner_2]["college"]["letter"], "D")
        # Check college balance calculation
        self.assertEqual(result["colleges"]["A"]["total"], 2000)
        self.assertEqual(result["colleges"]["D"]["total"], 300)
        # Check that the partner with no more shares is not in the register
        result = self.register(2022, 8, 13).get_shareholders()
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
        register = self.register(2022, 8, 13)
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
