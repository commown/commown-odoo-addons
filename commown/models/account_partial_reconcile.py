from odoo import models


class CommownAccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def step_workflow(self):
        return True
