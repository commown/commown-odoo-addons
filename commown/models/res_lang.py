from odoo import fields, models


class Lang(models.Model):
    _inherit = "res.lang"

    website_published = fields.Boolean()
