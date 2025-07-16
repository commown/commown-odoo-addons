from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    show_internal_followup = fields.Boolean("Show internal follow-up", default=False)
