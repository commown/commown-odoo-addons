from odoo.tests import HttpCase, tagged

from odoo.addons.website.tools import MockRequest

from ..controllers.main import WebsiteSaleCouponController
from .common import CouponTestMixin


@tagged("-at_install", "post_install")
class CouponControllersTC(CouponTestMixin, HttpCase):
    def test(self):
        self._create_coupon(code="MYCOUPON")
        so = self.sale_order()
        website = self.env.ref("website.default_website")

        with MockRequest(self.env, website=website, sale_order_id=so.id):
            result = WebsiteSaleCouponController().reserve_coupon("MYCOUPON")

        self.assertEqual(
            result,
            {"success": True, "coupons": [{"name": "MYCOUPON", "descr": "mycampaign"}]},
        )

        with MockRequest(self.env, website=website, sale_order_id=so.id):
            result = WebsiteSaleCouponController().reserved_coupons()

        self.assertEqual(result, [{"name": "MYCOUPON", "descr": "mycampaign"}])
