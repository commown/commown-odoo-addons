from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    name = fields.Char(translate=True)
