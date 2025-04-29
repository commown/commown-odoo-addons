from datetime import date

from .common import TestShareholderRegisterTC


class TestShareholderTagsUpdate(TestShareholderRegisterTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_move_lines = cls.env["account.move.line"]
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 3, 12), 2000)
        cls._add_shares(cls.partner_1, cls.account_porteur, (2018, 8, 12), -2000)
        cls._add_shares(cls.partner_2, cls.account_beneficiaire, (2018, 3, 12), 200)
        cls._add_shares(cls.partner_2, cls.account_soutien, (2018, 8, 12), 200)

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
