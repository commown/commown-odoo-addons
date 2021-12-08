import logging

from ..models.sale_order import CouponError

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSaleCouponController(http.Controller):

    def _coupon_descr(self, coupon):
        return {'name':  coupon.display_name,
                'descr': coupon.campaign_id.description}

    def _sale_coupons_descr(self, sale_order):
        return [self._coupon_descr(coupon)
                for coupon in sale_order.reserved_coupons()]

    @http.route('/website_sale_coupon/reserve_coupon', type='json',
                auth='public', website=True)
    def reserve_coupon(self, code):
        so = request.website.sale_get_order()
        try:
            coupon = so.reserve_coupon(code)
        except CouponError as exc:
            return {'success': False, 'reason': unicode(exc)}
        if coupon:
            return {'success': True, 'coupons': self._sale_coupons_descr(so)}
        else:
            return {'success': False}

    @http.route('/website_sale_coupon/reserved_coupons', type='json',
                auth='public', website=True)
    def reserved_coupons(self):
        return self._sale_coupons_descr(request.website.sale_get_order())
