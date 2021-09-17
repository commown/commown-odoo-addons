from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):

    env = Environment(cr, SUPERUSER_ID, {})
    for product in env['product.template'].search([]):
        product.website_description_sale = product.description_sale
