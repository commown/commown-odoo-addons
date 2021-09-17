from odoo import models, api

from .colissimo_utils import delivery_data


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def colissimo_delivery_data(self):
        self.ensure_one()
        return delivery_data(self)
