from odoo.tests.common import SavepointCase, tagged


@tagged("post_install", "-at_install")
class CouponTC(SavepointCase):
    def test_action_in_views(self):
        "Check the coupon file generating action is present in views"
        view = self.env.ref("website_sale_coupon.coupon_campaign_form")

        view_results = self.env["coupon.campaign"].get_views(
            [(view.id, "form"), (view.id, "list")],
            {"toolbar": True},
        )

        self.assertIn(
            "[commown] Generate PDF file of 65 new coupons",
            [a["name"] for a in view_results["views"]["form"]["toolbar"]["action"]],
        )
        self.assertIn(
            "[commown] Generate PDF file of 65 new coupons",
            [a["name"] for a in view_results["views"]["list"]["toolbar"]["action"]],
        )

    def test_action_generate_and_print_coupons(self):
        campaign = self.env["coupon.campaign"].create({"name": "test", "seller_id": 1})

        action = campaign.action_generate_and_print_coupons()
        att = self.env["ir.attachment"].search(
            [("res_model", "=", campaign._name), ("res_id", "=", campaign.id)],
        )

        self.assertEqual(action["url"], att.local_url + "&download=1")
        self.assertEqual(att.mimetype, "application/pdf")
        coupon_codes = campaign.coupon_ids.mapped("code")
        self.assertTrue(all(code in att.index_content for code in coupon_codes))
