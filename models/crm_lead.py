from odoo import models, fields, api


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    start_contract_on_delivery = fields.Boolean(
        default='_default_perform_actions_on_delivery',
        string='Automatic contract start on delivery')

    @api.multi
    def delivery_perform_actions(self):
        super(CrmLead, self).delivery_perform_actions()
        for record in self.filtered('start_contract_on_delivery'):
            if record.name.startswith('[SO') and ']' in record.name:
                contract = record.env['contract.contract'].search([
                    ('name', 'like', record.name[1:record.name.index(']')]),
                ]).ensure_one()

                contract.mapped('contract_line_ids').update({
                    'date_start': record.delivery_date,
                })
                contract.update({
                    'is_auto_pay': True,
                    'recurring_next_date': record.delivery_date,
                })
