import datetime

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def get_contract(self):
        self.ensure_one()
        return self.env['account.analytic.account'].search([
            ('recurring_invoice_line_ids.sale_order_line_id',
             '=', self.so_line_id.id),
        ])

    def action_generate_picking(self):
        contract = self.get_contract()

        if contract.picking_ids.filtered(lambda p: p.state != 'cancel'):
            raise UserError(
                _('The contract has already non-canceled picking(s)!\n'
                  'Either cancel or validate one.')
            )

        picking = contract.send_all_picking()
        view = self.env.ref('stock.view_picking_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'name': _('Initial picking'),
            'views': [(view.id, 'form')],
        }

    def button_open_contract(self):
        contract = self.get_contract()
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

    @api.multi
    def delivery_perform_actions(self):
        "Validate shipping"
        super(CrmLead, self).delivery_perform_actions()
        picking = self.get_contract().picking_ids.filtered(
            lambda p: p.state == 'assigned')
        if len(picking) == 1:
            picking.do_new_transfer()
