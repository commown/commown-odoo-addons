import logging

from odoo import models, api, _


_logger = logging.getLogger(__name__)


class CouponError(Exception):
    pass


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
            coupons = order.reserved_coupons().filtered(
                lambda c: c.campaign_id.is_valid(order))
            if coupons:
                _logger.info('Confirming coupons ids %s for sale %s',
                             coupons.mapped('id'), order.name)
                try:
                    self._check_cumulative_coupon_rules()
                except CouponError as exc:
                    _logger.error(
                        'Unrespected coupon cumulation rules in sale %s'
                        ' confirmation: %s.\n This should never happen.'
                        ' Not associating any coupon!', order.id, exc)
                else:
                    for coupon in coupons:
                        if not coupon.used_for_sale_id:
                            coupon.update({'used_for_sale_id': order.id,
                                           'reserved_for_sale_id': False})

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
                and coupon.campaign_id.is_valid(self)):
            self._check_cumulative_coupon_rules(candidate=coupon)
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
    def _check_cumulative_coupon_rules(self, candidate=None):
        """ Return True if coupon cumulation rules are respected, raises a
        CouponError otherwise. """
        self.ensure_one()
        coupons = self.reserved_coupons()
        if candidate is not None:
            coupons += candidate

        # Check non_auto cumulation rule
        seen_non_auto_cumulative_campaign = set()
        for coupon in coupons:
            campaign = coupon.campaign_id
            if not campaign.can_auto_cumulate:
                if campaign in seen_non_auto_cumulative_campaign:
                    raise CouponError(_(u"Cannot use more than one %s coupon")
                                      % campaign.name)
                seen_non_auto_cumulative_campaign.add(campaign)

        # Check cumulation with other campaigns rule
        non_cumulable_coupons = coupons.filtered(
            lambda c: not c.campaign_id.can_cumulate)
        if len(non_cumulable_coupons) > 1:
            raise CouponError(
                _(u"Cannot cumulate those coupons: %s")
                % u", ".join(non_cumulable_coupons.mapped("code")))
        return True
