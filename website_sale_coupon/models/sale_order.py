import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class CouponSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        self.confirm_coupons()
        res = super(CouponSaleOrder, self).action_confirm()
        return res

    @api.multi
    def confirm_coupons(self):
        for order in self:
            coupons = order.reserved_coupons()
            if coupons:
                _logger.info('Confirming coupons ids %s for sale %s',
                             coupons.mapped('id'), order.name)
                if not self._check_exclusive_coupons():
                    _logger.warning(
                        'Found non-orphan exclusive coupon in order %s.'
                        ' Using one arbitrary exclusive coupon.', order.id)
                    coupons = coupons.filtered(
                        'campaign_id.coupons_are_exclusive')[0]
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

        no_coupon_campaign = self.env['coupon.campaign'].search([
            ('name', 'ilike', code.upper()),
            ('is_without_coupons', '=', True),
        ]).filtered(lambda c: c.name.upper() == code.upper())

        if no_coupon_campaign:
            coupon = Coupon.create({
                'campaign_id': no_coupon_campaign.id,
                'code': Coupon._compute_default_code(),
            })
        else:
            # Automatically-generated coupon codes are uppercase
            coupon = Coupon.search([('code', '=', code.upper())])

        if (coupon
                and not coupon.used_for_sale_id
                and self._check_exclusive_coupons(candidate=coupon)
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

    @api.multi
    def _check_exclusive_coupons(self, candidate=None):
        """ Return False if there is no use of an exclusive coupon along with
        another coupon in current order, True otherwise.
        """
        self.ensure_one()
        coupons = self.reserved_coupons()
        if candidate is not None:
            coupons += candidate
        if (len(coupons) > 1 and
                coupons.filtered('campaign_id.coupons_are_exclusive')):
            return False
        return True
