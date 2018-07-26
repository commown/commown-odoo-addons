import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class CouponSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def confirm_coupons(self):
        Coupon = self.env['coupon.coupon'].sudo()
        for order in self:
            coupons = Coupon.reserved_coupons(order)
            if coupons:
                _logger.info('Confirming coupons ids %s for sale %s',
                             coupons.mapped('id'), order.name)
                coupons.confirm_coupons()

    @api.multi
    def action_confirm(self):
        res = super(CouponSaleOrder, self).action_confirm()
        self.confirm_coupons()
        return res
