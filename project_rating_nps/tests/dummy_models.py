from odoo import fields, models


class NPS_DummyParentModel(models.Model):
    _name = "project_rating_nps.dummy.parent.model"
    _inherit = "rating.parent.mixin"


class NPS_DummyModel(models.Model):
    _name = "project_rating_nps.dummy.model"
    _inherit = "rating.mixin"

    parent_id = fields.Many2one("project_rating_nps.dummy.parent.model")

    def _rating_get_parent_field_name(self):
        return "parent_id"
