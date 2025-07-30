from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    name = fields.Char(translate=True)
    login_checkbox_message = fields.Char("Login checkbox message", translate=True)
    legal_notice_url = fields.Char("Legal notice URL", translate=True)
