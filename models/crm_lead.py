from odoo import models, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.multi
    def _track_template(self, tracking):
        res = super()._track_template(tracking)
        test_lead = self[0]
        changes, tracking_value_ids = tracking[test_lead.id]
        if 'stage_id' in changes and test_lead.stage_id.mail_template_id:
            res['stage_id'] = (test_lead.stage_id.mail_template_id,
                               {'composition_mode': 'mass_mail'})
        return res
