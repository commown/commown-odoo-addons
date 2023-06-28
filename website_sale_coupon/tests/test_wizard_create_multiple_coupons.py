from odoo.tests import common


class TestCreateMultipleCoupons(common.SavepointCase):
    @classmethod
    def setUpClass(cls):

        super(TestCreateMultipleCoupons, cls).setUpClass()

        cls.partner_test_campaign = cls.env["res.partner"].create(
            {"name": "Partner test campaign"}
        )

        cls.campaign = cls.env["coupon.campaign"].create(
            {
                "name": "Test campaign",
                "seller_id": cls.partner_test_campaign.id,
            }
        )

    def test_create_multiple_coupons(self):
        coupon_number = 13
        wizard_view_action = (
            self.env["website_sale_coupon.create_multiple_coupons_wizard"]
            .create(
                {
                    "campaign_id": self.campaign.id,
                    "coupon_nb": coupon_number,
                }
            )
            .button_create_and_open_coupons()
        )
        created_coupons = self.env["coupon.coupon"].search(
            [("campaign_id.id", "=", self.campaign.id)]
        )
        self.assertEqual(len(created_coupons), coupon_number)
        self.assertEqual(
            [("id", "in", created_coupons.ids)], wizard_view_action["domain"]
        )
