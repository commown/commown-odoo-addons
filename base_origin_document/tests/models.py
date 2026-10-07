from odoo import fields, models


class TestDummyModel(models.Model):
    _name = "test.dummy.model"
    _inherit = "origin_document.mixin"

    name = fields.Char()
