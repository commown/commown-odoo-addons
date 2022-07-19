import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_equity = fields.Boolean("Is equity product")
    equity_type = fields.Selection(
        [("crowd", "Crowd equity"), ("invest", "Investment")],
        "Equity type",
        default="crowd",
        required=True,
        help="Equity type: crowd are limited to 1 per person",
    )

    @api.multi
    def is_crowd_equity(self):
        return all(p.is_equity and p.equity_type == "crowd" for p in self)

    @api.multi
    def is_investment(self):
        return all(p.is_equity and p.equity_type == "invest" for p in self)
