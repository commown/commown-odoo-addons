from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestShareholderRegisterTC(TransactionCase):
    "Common class for the tests of this module"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

        cls.env.company.nominal_share_amount = 20

        cls.partner_1 = cls.env["res.partner"].create({"name": "Partner 1"})
        cls.partner_2 = cls.env["res.partner"].create({"name": "Partner 2"})
        cls.partner_3 = cls.env["res.partner"].create({"name": "Partner 3"})

        cls.account_porteur = cls._create_account("10134000", "Porteur de Projet")
        cls.account_soutien = cls._create_account("10136000", "Account Soutien")
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
        cls.cat_soutien = cls._create_category(
            "Soutien",
            cls.account_soutien,
            cls.college_D,
            5,
        )
        cls.cat_beneficiaire = cls._create_category(
            "Beneficiare",
            cls.account_beneficiaire,
            cls.college_B,
            1,
        )

    @classmethod
    def _create_account(cls, code, name):
        account = cls.env["account.account"].create(
            {
                "name": name,
                "code": code,
                "account_type": "income_other",
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
            .search(
                [("type", "=", "general"), ("company_id", "=", account.company_id.id)],
                limit=1,
            )
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
