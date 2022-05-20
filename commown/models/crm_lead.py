from odoo import models, fields, api


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    def _default_perform_actions_on_delivery(self):
        return super(CrmLead, self)._default_perform_actions_on_delivery()

    start_contract_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string='Automatic contract start on delivery')

    @api.multi
    def delivery_perform_actions(self):
        super(CrmLead, self).delivery_perform_actions()
        for record in self.filtered('start_contract_on_delivery'):
            contract = record.contract_id.sudo()
            contract.is_auto_pay = True
            for cline in contract.contract_line_ids:
                cline.date_start = record.delivery_date
                cline._onchange_date_start()
            contract._compute_date_end()
