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
            if record.name.startswith('[SO') and ']' in record.name:
                contract = record.env['account.analytic.account'].search([
                    ('name', 'like', record.name[1:record.name.index(']')]),
                ]).ensure_one()

                contract.update({
                    'date_start': record.delivery_date,
                    'is_auto_pay': True,
                })
                # Perform date coherency check after delivery date update
                # as date_start is always before recurring_next_date here:
                contract.update({'recurring_next_date': record.delivery_date})
