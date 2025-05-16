import logging

from odoo import http
from odoo.http import request

from ..models.sale_order import CouponError

_logger = logging.getLogger(__name__)


class WebsiteSaleCouponController(http.Controller):
    @http.route(
        "/website_sale_coupon/reserve_coupon", type="json", auth="public", website=True
    )
    def reserve_coupon(self, code):
        so = request.website.sale_get_order()
        try:
            coupon = so.reserve_coupon(code)
        except CouponError as exc:
            return {"success": False, "reason": str(exc)}
        if coupon:
            return {"success": True, "coupons": so._sale_coupons_descr()}
        else:
            return {"success": False}

    @http.route(
        "/website_sale_coupon/reserved_coupons",
        type="json",
        auth="public",
        website=True,
    )
    def reserved_coupons(self):
        return request.website.sale_get_order()._sale_coupons_descr()
