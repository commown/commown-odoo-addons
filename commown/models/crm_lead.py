from odoo import api, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    def _default_perform_actions_on_delivery(self):
        return super(CrmLead, self)._default_perform_actions_on_delivery()

    @api.multi
    def delivery_perform_actions(self):
        super(CrmLead, self).delivery_perform_actions()
        for record in self:
            contract = record.contract_id.sudo()
            for cline in contract.contract_line_ids:
                cline.date_start = record.delivery_date
                cline._onchange_date_start()
            contract._compute_date_end()
