import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSaleCouponController(http.Controller):

    def _coupon_descr(self, coupon):
        return {'code': coupon.code, 'descr': coupon.campaign_id.description}

    @http.route('/website_sale_coupon/reserve_coupon', type='json',
                auth='public', website=True)
    def reserve_coupon(self, code):
        coupon = request.env['coupon.coupon'].sudo().reserve_coupon(
            code, request.website.sale_get_order())
        if coupon is not None:
            return {'success': True, 'descr': self._coupon_descr(coupon)}
        return {'success': False}

    @http.route('/website_sale_coupon/reserved_coupons', type='json',
                auth='public', website=True)
    def reserved_coupons(self):
        coupons = request.env['coupon.coupon'].sudo().reserved_coupons(
            request.website.sale_get_order())
        return [self._coupon_descr(coupon) for coupon in coupons]
