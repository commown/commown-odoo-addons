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
