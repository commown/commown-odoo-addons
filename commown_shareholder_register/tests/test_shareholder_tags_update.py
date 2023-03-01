from datetime import date

from odoo.tests import common

SHAREHOLDER_TAG_XML_ID = "commown_shareholder_register.shareholder_tag"
COLLEGE_A_XML_ID = "commown_shareholder_register.shareholder_tag_col_A"
COLLEGE_B_XML_ID = "commown_shareholder_register.shareholder_tag_col_B"
COLLEGE_C_XML_ID = "commown_shareholder_register.shareholder_tag_col_C"
COLLEGE_D_XML_ID = "commown_shareholder_register.shareholder_tag_col_D"


class TestShareholderTagsUpdate(common.SavepointCase):
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
    def _create_college(cls, name, rank):
        college = cls.env["commown_shareholder_register.college"].create(
            {
                "name": name,
                "rank": rank,
            }
        )
        return college

    @classmethod
    def _create_category(cls, name, account, college, min_share_number):
        category = cls.env["commown_shareholder_register.category"].create(
            {
                "name": name,
                "account_id": account.id,
                "college_id": college.id,
                "min_share_number": min_share_number,
            }
        )
        return category

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

        super(TestShareholderTagsUpdate, cls).setUpClass()
        cls.env["res.company"].browse(1).nominal_share_amount = 20

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

        cls.college_A = cls._create_college("A", 80)
        cls.college_B = cls._create_college("B", 30)
        cls.college_D = cls._create_college("D", 40)

        cls.cat_porteur = cls._create_category(
            "Porteur",
            cls.account_porteur,
            cls.college_A,
            100,
        )
        cls.cat_soutient = cls._create_category(
            "Soutient",
            cls.account_soutient,
            cls.college_D,
            5,
        )
        cls.cat_beneficiaire = cls._create_category(
            "Beneficiare",
            cls.account_beneficiaire,
            cls.college_B,
            1,
        )

        cls.account_move_lines = cls.env["account.move.line"]
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 3, 12), 2000)
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 8, 12), -2000)
        cls._add_shares(cls.partner_2, cls.account_beneficiaire, (2018, 3, 12), 200)
        cls._add_shares(cls.partner_2, cls.account_soutient, (2018, 8, 12), 200)

    def update_tags(self, *date_tuple):
        self.env["commown_shareholder_register.shareholder_tags_update"].create(
            {"date": date(*date_tuple)}
        ).action_update_partners_tag()

    def test_tags_update(self):
        self.update_tags(2018, 3, 13)
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag"),
            self.partner_1.category_id,
        )
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag_col_A"),
            self.partner_1.category_id,
        )
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag"),
            self.partner_2.category_id,
        )
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag_col_B"),
            self.partner_2.category_id,
        )
        self.update_tags(2018, 8, 13)

        self.assertNotIn(
            self.env.ref("commown_shareholder_register.shareholder_tag"),
            self.partner_1.category_id,
        )
        self.assertNotIn(
            self.env.ref("commown_shareholder_register.shareholder_tag_col_A"),
            self.partner_1.category_id,
        )
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag"),
            self.partner_2.category_id,
        )
        self.assertIn(
            self.env.ref("commown_shareholder_register.shareholder_tag_col_D"),
            self.partner_2.category_id,
        )
        self.assertNotIn(
            self.env.ref("commown_shareholder_register.shareholder_tag_col_B"),
            self.partner_2.category_id,
        )
