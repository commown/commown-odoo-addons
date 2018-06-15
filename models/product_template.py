import logging

from odoo import models, fields
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class RentalProductTemplate(models.Model):
    _inherit = 'product.template'

    is_rental = fields.Boolean('Is rental product')
    deposit_price_to_lease_amount_ratio = fields.Float(
        'Deposit price to lease amount ratio', default=2,
        digits=dp.get_precision('Product Price'))
    rental_frequency = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
         ('yearly', 'Yearly')], 'Rental payment frequency',
        default='monthly', help='Frequency of the rental price payment',
        required=True)
    rental_contract_tmpl_id = fields.Many2one(
        'account.analytic.contract', string='Rental contract template')
