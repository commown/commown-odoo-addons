import datetime

from odoo import _, api, models
from odoo.exceptions import UserError

from .common import do_new_transfer


def _assigned(picking):
    return picking.state == "assigned"


class CrmLead(models.Model):
    _inherit = "crm.lead"
    delivery_time = datetime.time(9, 0)

    def action_generate_picking(self):
        contract = self.contract_id

        if contract.picking_ids.filtered(lambda p: p.state == "assigned"):
            raise UserError(
                _(
                    "The contract has already assigned picking(s)!\n"
                    "Either cancel, scrap or validate it."
                )
            )

        view = self.env.ref("commown_devices.wizard_crm_lead_picking_form")
        return {
            "type": "ir.actions.act_window",
            "src_model": "crm.lead",
            "res_model": "crm.lead.picking.wizard",
            "name": _("Send a device"),
            "views": [(view.id, "form")],
            "target": "new",
            "context": {"default_lead_id": self.id},
        }

    @api.multi
    def write(self, values):
        res = super().write(values)
        stage_id = values.get("stage_id")
        if stage_id:
            stage = self.env["crm.stage"].browse(stage_id)
            if "[stock: check-has-picking]" in stage.name:
                self.action_check_waiting_picking()
        return res

    def action_check_waiting_picking(self):
        if self.so_line_id.product_id.product_tmpl_id.storable_product_id:
            if not self.contract_id.picking_ids.filtered(_assigned):
                raise UserError(_("Lead has no assigned picking."))

    @api.multi
    def delivery_perform_actions(self):
        "Validate shipping"
        super(CrmLead, self).delivery_perform_actions()
        picking = self.contract_id.picking_ids.filtered(_assigned)
        if len(picking) == 1:
            # time doesn't really matter for now; ideally
            # deliver_date would become delivery_datetime:
            do_new_transfer(
                picking,
                datetime.datetime.combine(self.delivery_date, self.delivery_time),
            )
