from odoo import fields, models


class WizardForcePartnerOnMoveLine(models.TransientModel):
    _name = "wizard.force.partner.on.move.line"
    _description = "Force-write a differing partner on a move line through SQL"

    move_id = fields.Many2one(comodel_name="account.move", required=True)
    line_to_change_id = fields.Many2one(
        comodel_name="account.move.line",
        domain="[('move_id', '=', move_id)]",
        required=True,
    )

    new_partner_id = fields.Many2one(comodel_name="res.partner", required=True)

    def execute(self):
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE account_move_line SET partner_id = %s WHERE id = %s",
            (self.new_partner_id.id, self.line_to_change_id.id),
        )

        return {"type": "ir.actions.client", "tag": "reload"}
