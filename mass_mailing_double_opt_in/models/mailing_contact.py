from odoo import fields, models


class DoubleOptInMailingContact(models.Model):
    _inherit = "mailing.contact"

    ip_addr = fields.Char("IP Address used for subscription", readonly=True)
