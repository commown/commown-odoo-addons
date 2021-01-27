from odoo import models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def slimpay_payment_issue_process_automatically(self):
        """ Handle a payment issue automatically only when it comes from a
        contract generated invoice.
        """
        self.ensure_one()
        return bool(self.invoice_id.contract_id)
