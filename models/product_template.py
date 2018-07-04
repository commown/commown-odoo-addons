import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class SupportedProductTemplate(models.Model):
    """ Add groups to products, where users who bought the product are
    automatically added.
    """
    _inherit = 'product.template'

    support_group_ids = fields.Many2many(
        'res.groups', 'supported_product_tmpl_ids', string='Support groups')
    followup_sales_team_id = fields.Many2one(
        'crm.team', string='Followup sales team')
