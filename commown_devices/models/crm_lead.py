from odoo import _, api, models
from odoo.exceptions import UserError

from .common import ToCustomerPickingMixin


class CrmLead(ToCustomerPickingMixin, models.Model):
    _inherit = "crm.lead"

    @api.constrains("stage_id")
    def _check_picking_on_stage_change(self):
        if self.stage_id.name:
            if "[stock: check-has-picking]" in self.stage_id.name:
                self.action_check_waiting_picking()

    def action_check_waiting_picking(self):
        if self.so_line_id.product_id.primary_storable_variant_id:
            if not self.contract_id.pending_picking():
                raise UserError(_("Lead has no assigned picking."))
