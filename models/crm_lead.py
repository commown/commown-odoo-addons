import datetime

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_generate_picking(self):
        contract = self.contract_id

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

    @api.multi
    def delivery_perform_actions(self):
        "Validate shipping"
        super(CrmLead, self).delivery_perform_actions()
        picking = self.contract_id.picking_ids.filtered(
            lambda p: p.state == 'assigned')
        if len(picking) == 1:
            picking.do_new_transfer()
