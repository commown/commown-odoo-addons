import string
import random
from datetime import datetime

from odoo import models, fields, api


class Campaign(models.Model):
    _name = 'coupon.campaign'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Campaign already exists!"),
    ]

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    date_start = fields.Date(
        'Validity start date', help='Leave empty to start now')
    date_end = fields.Date(
        'Validity end date', help='Leave empty for no end')
    seller_id = fields.Many2one(
        'res.partner', string='Partner who sales the coupons', required=True)
    target_product_tmpl_ids = fields.Many2many(
        'product.template', string='Target products', help='(all if empty)')
    coupon_ids = fields.One2many(
        'coupon.coupon', 'campaign_id', string='Coupons of the campaign',
        index=True)
    emitted_coupons = fields.Integer(
        'Emitted coupons',
        compute='_compute_emitted_coupons', store=True, compute_sudo=True)
    used_coupons = fields.Integer(
        'Used coupons',
        compute='_compute_used_coupons', store=False, compute_sudo=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if (self.date_start and self.date_end
                and self.date_start > self.date_end):
            raise models.ValidationError('Start date must be before end date')

    @api.depends('coupon_ids')
    def _compute_emitted_coupons(self):
        for record in self:
            record.emitted_coupons = len(record.coupon_ids)

    def _compute_used_coupons(self):
        for record in self:
            record.used_coupons = len(
                record.coupon_ids.filtered('used_for_sale_id'))

    @api.multi
    def is_valid(self, sale_order):
        """ Return True if current campaign is valid today (according to its
        start and end dates) for the given sale order (comparing its eligible
        to the sold products).
        """
        self.ensure_one()

        # Check dates
        today = datetime.now().date().strftime(fields.DATE_FORMAT)
        if self.date_start and self.date_start > today:
            return False
        if self.date_end and self.date_end < today:
            return False

        # Check products
        if self.target_product_tmpl_ids:
            target_product_tmpl_ids = set(
                pt.id
                for pt in self.target_product_tmpl_ids)
            sold_product_tmpl_ids = set(
                l.product_id.product_tmpl_id.id
                for l in sale_order.order_line if l.product_uom_qty > 0)
            if not target_product_tmpl_ids.intersection(sold_product_tmpl_ids):
                return False

        return True


class Coupon(models.Model):
    _name = 'coupon.coupon'

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "This coupon code is already used!"),
    ]

    _coupon_code_size = 10
    _coupon_allowed_chars = string.ascii_uppercase + string.digits

    def _compute_default_code(self):
        return ''.join(random.choice(self._coupon_allowed_chars)
                       for _char in range(self._coupon_code_size))

    campaign_id = fields.Many2one(
        'coupon.campaign', string='Campaign of the coupon', required=True,
        ondelete='cascade')
    code = fields.Char(
        string="Code", size=_coupon_code_size, index=True,
        default=_compute_default_code)
    used_for_sale_id = fields.Many2one('sale.order', string='Used for sale')
    reserved_for_sale_id = fields.Many2one(
        'sale.order', string='Reserved for sale (admin info only)')

    def reserve_coupon(self, code, sale_order):
        """ Return a coupon from given code and sale_order if there is one
        with that code, that is also unused and valid for given sale order.
        """
        coupon = self.search([('code', '=', code)])
        if (coupon
                and not coupon.used_for_sale_id
                and coupon.campaign_id.is_valid(sale_order)):
            coupon.reserved_for_sale_id = sale_order.id
            return coupon

    def reserved_coupons(self, sale_order):
        return self.search([('reserved_for_sale_id', '=', sale_order.id)])

    def used_coupons(self, sale_order):
        return self.search([('used_for_sale_id', '=', sale_order.id)])

    @api.multi
    def confirm_coupons(self):
        """ Confirm the coupons that were reserved (i.e. input by the user)
        for a sale order. The coupons' validity is checked again to avoid
        user tricks like adding another product then removing the one which
        gives the access to the coupon.
        """
        for coupon in self:
            order = coupon.reserved_for_sale_id
            if order and not coupon.used_for_sale_id:
                if coupon.campaign_id.is_valid(order):
                    coupon.update({'used_for_sale_id': order.id,
                                   'reserved_for_sale_id': False})
                else:
                    coupon.update({'reserved_for_sale_id': False})
