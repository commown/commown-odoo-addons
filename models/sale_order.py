import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class CouponSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super(CouponSaleOrder, self).action_confirm()
        self.confirm_coupons()
        return res

    @api.multi
    def confirm_coupons(self):
        for order in self:
            coupons = order.reserved_coupons()
            if coupons:
                _logger.info('Confirming coupons ids %s for sale %s',
                             coupons.mapped('id'), order.name)
            for coupon in coupons:
                if not coupon.used_for_sale_id:
                    if coupon.campaign_id.is_valid(order):
                        coupon.update({'used_for_sale_id': order.id,
                                       'reserved_for_sale_id': False})
                    else:
                        coupon.update({'reserved_for_sale_id': False})

    @api.multi
    def reserve_coupon(self, code):
        """ Return a coupon from given code if there is one with that code,
        that is also unused and valid for current sale order.
        """
        self.ensure_one()
        Coupon = self.env['coupon.coupon'].sudo()
        coupon = Coupon.search([('code', '=', code)])
        if (coupon
                and not coupon.used_for_sale_id
                and coupon.campaign_id.is_valid(self)):
            coupon.reserved_for_sale_id = self.id
            return coupon

    @api.multi
    def reserved_coupons(self):
        self.ensure_one()
        Coupon = self.env['coupon.coupon'].sudo()
        return Coupon.search([('reserved_for_sale_id', '=', self.id)])

    @api.multi
    def used_coupons(self):
        self.ensure_one()
        Coupon = self.env['coupon.coupon'].sudo()
        return Coupon.search([('used_for_sale_id', '=', self.id)])
