from odoo import models


class Project(models.Model):
    _name = "project.project"
    _inherit = [
        "project.project",
        "commown.delivery.parent.mixin",
    ]
