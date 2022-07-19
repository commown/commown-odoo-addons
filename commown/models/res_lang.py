from odoo import models, fields


class Lang(models.Model):
    _inherit = "res.lang"

    website_published = fields.Boolean()
