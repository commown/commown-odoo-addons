from odoo import models, fields


class UrbanMinePartner(models.Model):
    _inherit = 'res.partner'

    from_urban_mine = fields.Boolean(string='From urban mine registration',
                                     website_form_blacklisted=False)
