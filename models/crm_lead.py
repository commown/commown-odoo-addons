from odoo import models, _


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def button_open_contract(self):
        contract = self.env['account.analytic.account'].search([
            ('recurring_invoice_line_ids.sale_order_line_id',
             '=', self.so_line_id.id),
        ])
        view = self.env.ref(
            'contract.account_analytic_account_recurring_form_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'res_id': contract.id,
            'name': _('Related contracts'),
            'context': {'is_contract': 1},
            'views': [(view.id, 'form')],
        }
