from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class SaleOrderTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so = cls.env.ref("sale.portal_sale_order_1")
        cls.user = cls.so.partner_id.user_ids

    def test_add_receivable_account(self):
        "Buying a product must add the buyer a dedicated receivable account"

        self.so.action_confirm()

        account = self.so.partner_id.property_account_receivable_id
        self.assertEqual(account.name, self.so.partner_id.name)
        self.assertEqual(account.code, "411.C.%d" % self.so.partner_id.id)

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
        self.assertEqual(account.code, "411.C.%d" % company.id)
        self.assertEqual(account, company.property_account_receivable_id)
        self.assertEqual(account, collegue.property_account_receivable_id)

    def test_add_receivable_account_already_exists(self):
        """When a buyer's account already exists but is not set, it is set to
        the existing account (and there is no crash creating an account with
        the same name)"""

        partner = self.so.partner_id
        expected_code = "411.C.%s" % partner.id
        self.assertNotEqual(partner.property_account_receivable_id.code, expected_code)

        account = self.env["account.account"].create(
            {
                "code": expected_code,
                "name": partner.name,
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )

        self.so.action_confirm()

        self.assertEqual(partner.property_account_receivable_id, account)
