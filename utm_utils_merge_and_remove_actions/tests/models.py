from odoo import models


class TestUtmDummy(models.Model):
    _name = "test.utm_dummy"
    _inherit = "utm.mixin"
