from odoo import api, fields, models


class CommownAccountMoveLine(models.Model):

    _inherit = "account.move.line"

    full_reconcile_id = fields.Many2one(index=True)

    @api.multi
    def step_workflow(self):
        return True
