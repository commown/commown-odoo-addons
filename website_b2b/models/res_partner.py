from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    website_id = fields.Many2one(
        help="Website the user can log in. An empty value means all websites."
    )
