from odoo import api, models


class CommownAccountPartialReconcile(models.Model):

    _inherit = "account.partial.reconcile"

    @api.multi
    def step_workflow(self):
        return True
