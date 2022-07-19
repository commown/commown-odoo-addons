from odoo import api, models


class CommownAccountMoveLine(models.Model):

    _inherit = "account.move.line"

    @api.multi
    def step_workflow(self):
        return True
