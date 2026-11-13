from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .common import _force_picking_date


class ForcePickingDateWizardLine(models.TransientModel):
    _name = "force.picking.date.wizard.line"

    wizard_id = fields.Many2one("force.picking.date.wizard")

    ## Readonly fields
    picking_id = fields.Many2one("stock.picking", required=True)

    orig_location = fields.Many2one("stock.location", compute="_compute_locations")
    dest_location = fields.Many2one("stock.location", compute="_compute_locations")

    def get_lot_move_line(self):
        return self.picking_id.move_line_ids.filtered_domain(
            [("lot_id", "=", self.wizard_id.concerned_lot.id)]
        )

    @api.depends("picking_id")
    def _compute_locations(self):
        for line in self:
            move_line = line.get_lot_move_line()
            line.orig_location = move_line.location_id
            line.dest_location = move_line.location_dest_id

    ## Editable fields
    new_date = fields.Datetime(required=True)
    is_date_different = fields.Boolean(compute="_compute_is_date_different")

    @api.depends("new_date")
    def _compute_is_date_different(self):
        for line in self:
            line.is_date_different = line.new_date != line.picking_id.date_done


class ForcePickingDateWizard(models.TransientModel):
    _name = "force.picking.date.wizard"

    wizard_line_ids = fields.One2many(
        "force.picking.date.wizard.line", inverse_name="wizard_id"
    )

    concerned_lot = fields.Many2one("stock.lot", required=True, readonly=True)

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        active_id = self.env.context.get("active_id", False)
        if active_id:
            picking = self.env["stock.picking"].browse(active_id)
            lot = picking.move_line_ids.lot_id

            all_picks = (
                self.env["stock.move.line"]
                .search(
                    [
                        ("lot_id", "=", lot.id),
                        ("state", "=", "done"),
                    ]
                )
                .mapped("move_id.picking_id")
            )
            rec.update(
                {
                    "concerned_lot": lot.id,
                    "wizard_line_ids": [
                        (0, 0, {"picking_id": pick.id, "new_date": pick.date_done})
                        for pick in all_picks
                    ],
                }
            )
        return rec

    is_history_coherent = fields.Boolean(
        "Coherent history", compute="_compute_is_history_coherent"
    )

    @api.depends("wizard_line_ids.new_date")
    def _compute_is_history_coherent(self):
        coherent = True
        prev_loc = self.env["stock.location"]
        wizard_history = self.wizard_line_ids.sorted(lambda l: l.new_date)

        for line in wizard_history:
            if prev_loc and prev_loc != line.orig_location:
                coherent = False
                break
            prev_loc = line.dest_location

        self.is_history_coherent = coherent

    def execute(self):
        if not self.is_history_coherent:
            raise UserError(
                _(
                    "The described device history is incoherent -"
                    " please fix it before applying the changes."
                )
            )

        for line in self.wizard_line_ids.filtered("is_date_different"):
            self.env.cr.execute(
                "UPDATE stock_picking SET scheduled_date = %s WHERE id = %s",
                (str(line.new_date), line.picking_id.id),
            )
            _force_picking_date(line.picking_id, line.new_date)
