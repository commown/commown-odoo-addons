from odoo.tests.common import tagged

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class CouponSaleOrderTC(RentalSaleOrderTC):
    def test_add_followup_card_name_with_coupon(self):
        """Followup card name must indicate sale coupons were used if any"""

        partner = self.env.ref("base.partner_demo_portal")
        so = self.create_sale_order(partner)

        # Setting up the CRM pipeline
        # (We assign 2 products to the test team's pipeline)
        team = self.env["crm.team"].create({"name": "Test team", "use_leads": True})
        self.env["crm.stage"].create(
            {"team_id": team.id, "name": "test [stage: start]"}
        )

        self.env["product.product"].search(
            [
                ("name", "in", ["Fairphone Premium", "PC"]),
                ("id", "in", so.mapped("order_line.product_id").ids),
            ]
        ).update({"followup_sales_team_id": team.id})

        # Simulate the usage of a coupon in the sale:
        campaign = self.env["coupon.campaign"].create(
            {
                "name": "Test campaign 40% reduction",  # % used deliberately here
                "seller_id": self.env.ref("base.res_partner_1").id,
            }
        )
        self.env["coupon.coupon"].create(
            {
                "reserved_for_sale_id": so.id,
                "campaign_id": campaign.id,
            }
        )

        # Trigger the automatic action
        so.action_confirm()

        # Check effects
        leads = self.env["crm.lead"].search(
            [
                ("partner_id", "=", partner.id),
                ("name", "ilike", "%" + so.name + "%"),
            ]
        )
        self.assertEqual(len(leads), 3)
        self.assertTrue(
            all("COUPON: %s" % campaign.name in name for name in leads.mapped("name"))
        )
