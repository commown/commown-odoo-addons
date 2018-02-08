import logging

from odoo import models, fields
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class RentalProductTemplate(models.Model):
    _inherit = 'product.template'

    is_rental = fields.Boolean('Is rental product')
    rental_price = fields.Float(
        'Rental price', digits=dp.get_precision('Product Price'))
    rental_frequency = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
         ('yearly', 'Yearly')], 'Rental payment frequency',
        default='monthly', help='Frequency of the rental price payment',
        required=True)
