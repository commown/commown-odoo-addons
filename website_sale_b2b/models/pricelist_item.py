from odoo import models


class PriceListItem(models.Model):
    _inherit = "product.pricelist.item"

    _order = "id desc"
