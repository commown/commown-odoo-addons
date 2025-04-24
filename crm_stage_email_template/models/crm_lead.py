from odoo import models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _track_template(self, changes):
        res = super()._track_template(changes)
        test_lead = self[0]

        if "stage_id" in changes and test_lead.stage_id.mail_template_id:
            res["stage_id"] = test_lead.stage_id.mail_template_id, {}
        return res
