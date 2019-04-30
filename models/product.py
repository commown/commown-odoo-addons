from odoo import models, fields


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    shipping_parcel_type_id = fields.Many2one(
        'commown.parcel.type', string='Parcel type')
