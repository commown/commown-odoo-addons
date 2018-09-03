from odoo import models, fields


class SaleAffiliate(models.Model):
    _inherit = 'sale.affiliate'

    restriction_product_tmpl_ids = fields.Many2many(
        'product.template', string='Restrict to products',
        help=('If not empty, only sales that contain at least one of these'
              ' products considered part of the affiliation.'),
        )
