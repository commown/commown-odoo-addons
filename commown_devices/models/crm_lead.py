import datetime

from odoo import _, api, models
from odoo.exceptions import UserError

from .common import do_new_transfer


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
    def delivery_perform_actions(self):
        "Validate shipping"
        super(CrmLead, self).delivery_perform_actions()
        picking = self.contract_id.picking_ids.filtered(lambda p: p.state == "assigned")
        if len(picking) == 1:
            # time doesn't really matter for now; ideally
            # deliver_date would become delivery_datetime:
            do_new_transfer(
                picking,
                datetime.datetime.combine(self.delivery_date, self.delivery_time),
            )
