from odoo.tests import common


class TestCreateMultipleCoupons(common.SavepointCase):
    @classmethod
    def setUpClass(cls):

        super(TestCreateMultipleCoupons, cls).setUpClass()

        cls.partner_test_campaign = cls.env["res.partner"].create(
            {"name": "Partner test campaign"}
        )
        cls.campaign = cls.env["coupons.campain"].create(
            {
                "name": "Test camapign",
                "partner_id": cls.partner_test_campaign.id,
            }
        )

    def test_create_multiple_coupons(self):
        coupon_number = 13
        self.env["website_sale_coupon.create_multiple_coupons_wizard"].create(
            {
                "campaign_id": self.campaign.id,
                "coupon_nb": coupon_number,
            }
        ).create_multiple_coupons()
        created_coupons = self.env[
            "website_sale_coupon.create_multiple_coupons_wizard"
        ].search([("campaign_id", "=", self.campaign)])
        self.assertEqual(len(created_coupons), coupon_number)
