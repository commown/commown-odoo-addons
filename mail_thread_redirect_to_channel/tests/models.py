from odoo import fields, models


class Redirect_DummyModel(models.Model):
    _name = "dummy.model"
    _inherit = "mail.thread"

    name = fields.Char()
    dummy_boolean = fields.Boolean()
