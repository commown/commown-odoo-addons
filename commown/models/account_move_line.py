from odoo import fields, models


class CommownAccountMoveLine(models.Model):
    _inherit = "account.move.line"

    full_reconcile_id = fields.Many2one(index=True)

    def step_workflow(self):
        return True
