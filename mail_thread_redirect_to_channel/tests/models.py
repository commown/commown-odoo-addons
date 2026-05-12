from odoo import fields, models


class Redirect_DummyModel(models.Model):
    _name = "dummy.model"
    _description = "Dummy model for testing purposes"
    _inherit = "mail.thread"

    name = fields.Char()
    dummy_boolean = fields.Boolean()
