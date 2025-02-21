import datetime

from odoo import _, api, models
from odoo.exceptions import UserError

from .common import ToCustomerPickingMixin, _assigned, do_new_transfer


class CrmLead(ToCustomerPickingMixin, models.Model):
    _inherit = "crm.lead"
    delivery_time = datetime.time(9, 0)

    @api.constrains("stage_id")
    def _check_picking_on_stage_change(self):
        if self.stage_id.name:
            if "[stock: check-has-picking]" in self.stage_id.name:
                self.action_check_waiting_picking()

    def action_check_waiting_picking(self):
        if self.so_line_id.product_id.primary_storable_variant_id:
            if not self.contract_id.pending_picking():
                raise UserError(_("Lead has no assigned picking."))

    @api.multi
    def delivery_perform_actions(self):
        "Validate shipping"
        super(CrmLead, self).delivery_perform_actions()
        picking = self.contract_id.move_ids.mapped("picking_id").filtered(_assigned)
        if len(picking) == 1:
            # time doesn't really matter for now; ideally
            # deliver_date would become delivery_datetime:
            do_new_transfer(
                picking,
                datetime.datetime.combine(self.delivery_date, self.delivery_time),
            )
