from odoo import fields, models


class CommownPartner(models.Model):
    _inherit = "project.task.type"

    portal_displayed_name = fields.Char(
        "Name displayed on the portal", size=100, translate=True
    )
