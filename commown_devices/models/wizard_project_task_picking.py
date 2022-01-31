from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .common import internal_picking


class ProjectTaskPickingWizard(models.Model):
    _name = "project.task.picking.wizard"

    destination_refs = (
        "stock_location_outsourced_repair",
        "stock_location_repackaged_devices",
        "stock_location_devices_to_check",
        "stock_location_repairer",
    )

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
    )

    location_dest_id = fields.Many2one(
        "stock.location",
        string="Destination",
        required=True,
    )

    date = fields.Datetime(
        string="date",
        help="Defaults to now - To be set only to force a date",
    )

    def present_location(self):
        return self.env["stock.quant"].search([
            ("lot_id", "=", self.task_id.lot_id.id)]).location_id

    def _possible_dest_locations(self):
        """ Possible destinations: all listed the `destination_ref` attribute
        and their children, excluding views.
        """
        orig_location = self.present_location()
        result = self.env["stock.location"]

        for ref in self.destination_refs:
            loc = self.env.ref("commown_devices.%s" % ref)
            if loc != orig_location:
                if loc.usage == "view":
                    result |= result.search([("id", "child_of", loc.id),
                                             ("usage", "!=", "view")])
                else:
                    result |= loc
        return result

    @api.onchange("task_id")
    def onchange_task_id(self):
        if self.task_id:
            dest_locations = self._possible_dest_locations()
            return {
                "domain": {
                    "location_dest_id": [("id", "in", dest_locations.ids)]
                }
            }

    @api.multi
    def create_picking(self):
        lot = self.task_id.lot_id

        if not lot:
            raise UserError(_("Can't move device: no device set on this task!"))

        return internal_picking(
            "Task-%s" % self.task_id.id, [lot], self.present_location(),
            self.location_dest_id, date=self.date, do_transfer=True)
