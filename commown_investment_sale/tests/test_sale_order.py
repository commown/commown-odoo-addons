from odoo.tests import tagged

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class SaleOrderTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        partner = self.env.ref("base.partner_demo_portal")
        self.user = partner.user_ids
        self.so = self.create_sale_order(partner)

    def test_investment_followup_card_creation(self):
        equity = self.env["product.product"].create(
            {
                "name": "Investment test product",
                "is_equity": True,
                "equity_type": "invest",
                "list_price": 60.0,
            }
        )
        self.so.update({"order_line": [self._oline(equity)]})

        project = self.env.ref("commown_investment_sale.investment_followup_project")
        self.assertFalse(project.task_count)

        self.so.action_confirm()

        self.assertEqual(project.task_count, 1)
        self.assertIn(self.so.name, project.task_ids.description)
        self.assertIn("Investment test product", project.task_ids.description)
