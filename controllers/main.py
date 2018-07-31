import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSaleCouponController(http.Controller):

    def _coupon_descr(self, coupon):
        return {'code': coupon.code, 'descr': coupon.campaign_id.description}

    def _sale_coupons_descr(self, sale_order):
        coupons = request.env['coupon.coupon'].sudo().reserved_coupons(
            sale_order)
        return [self._coupon_descr(coupon) for coupon in coupons]

    @http.route('/website_sale_coupon/reserve_coupon', type='json',
                auth='public', website=True)
    def reserve_coupon(self, code):
        so = request.website.sale_get_order()
        coupon = request.env['coupon.coupon'].sudo().reserve_coupon(code, so)
        if coupon is not None:
            return {'success': True, 'coupons': self._sale_coupons_descr(so)}
        return {'success': False}

    @http.route('/website_sale_coupon/reserved_coupons', type='json',
                auth='public', website=True)
    def reserved_coupons(self):
        return self._sale_coupons_descr(request.website.sale_get_order())
