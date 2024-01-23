from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    groups_id = fields.Many2many(
        "res.groups",
        string="Groups",
    )
