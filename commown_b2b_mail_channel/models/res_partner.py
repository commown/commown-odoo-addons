from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    _sql_constraints = [
        ("mail_channel_uniq", "unique (mail_channel_id)", "Channel already used!"),
    ]

    mail_channel_id = fields.Many2one(
        "mail.channel",
        string="Support mail chanel",
        domain=[("public", "=", "private"), ("channel_type", "=", "channel")],
    )
