from odoo.tests import tagged

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class SaleOrderTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        partner = self.env.ref("base.partner_demo_portal")
        self.user = partner.user_ids
        self.so = self.create_sale_order(partner)

        def p_by_name(name):
            return (
                self.env["product.product"]
                .search(
                    [
                        ("name", "=", name),
                        ("id", "in", self.so.mapped("order_line.product_id").ids),
                    ]
                )
                .ensure_one()
            )

        p1 = p_by_name("Fairphone Premium")
        p2 = p_by_name("PC")
        p1.followup_sales_team_id = self._create_sales_team(1).id
        p2.followup_sales_team_id = self._create_sales_team(3).id

    def _create_sales_team(self, num, **kwargs):
        kwargs.setdefault("name", "Test team%d" % num)
        kwargs.setdefault("use_leads", True)
        team = self.env["crm.team"].create(kwargs)
        for n in range(4):
            self.env["crm.stage"].create(
                {
                    "team_id": team.id,
                    "name": "test %d" % n if n != 1 else "test [stage: start]",
                }
            )
        return team

    def test_add_receivable_account(self):
        "Buying a product must add the buyer a dedicated receivable account"

        self.so.action_confirm()

        account = self.so.partner_id.property_account_receivable_id
        self.assertEqual(account.name, self.so.partner_id.name)
        self.assertEqual(account.code, "411-C-%d" % self.so.partner_id.id)
        self.assertEqual(account.tax_ids, self.env.ref("l10n_fr.1_tva_normale"))

    def test_add_receivable_account_with_children(self):
        """Buying a product in B2B must add the buyer's company and collegues a
        dedicated receivable account.
        """

        company = self.env.ref("base.res_partner_1")
        self.so.partner_id.parent_id = company.id
        collegue = self.env["res.partner"].create(
            {"name": "Toto", "parent_id": company.id},
        )

        self.so.action_confirm()

        account = self.so.partner_id.property_account_receivable_id
        self.assertEqual(account.code, "411-C-%d" % company.id)
        self.assertEqual(account, company.property_account_receivable_id)
        self.assertEqual(account, collegue.property_account_receivable_id)

    def test_add_receivable_account_already_exists(self):
        """When a buyer's account already exists but is not set, it is set to
        the existing account (and there is no crash creating an account with
        the same name)"""

        partner = self.so.partner_id
        expected_code = "411-C-%s" % partner.id
        self.assertNotEqual(partner.property_account_receivable_id.code, expected_code)

        ref = self.env.ref
        account = self.env["account.account"].create(
            {
                "code": expected_code,
                "name": partner.name,
                "tag_ids": [(6, 0, [ref("account.account_tag_operating").id])],
                "user_type_id": ref("account.data_account_type_receivable").id,
                "tax_ids": [(6, 0, ref("l10n_fr.1_tva_normale").ids)],
                "reconcile": True,
            }
        )

        self.so.action_confirm()

        self.assertEqual(partner.property_account_receivable_id, account)
