from odoo import _, fields, models


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
        initial_partner = self.line_to_change_id.partner_id
        self.env.cr.execute(
            "UPDATE account_move_line SET partner_id = %s WHERE id = %s",
            (self.new_partner_id.id, self.line_to_change_id.id),
        )

        self.move_id.message_post(
            body=_(
                """
                    Partner changed on move line '%(line_name)s' :
                    <ul>
                        <li>%(init_partner_name)s &#8594; %(new_partner_name)s</li>
                    </ul>
                """,
                line_name=self.line_to_change_id.name,
                init_partner_name=initial_partner.display_name,
                new_partner_name=self.new_partner_id.display_name,
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.client", "tag": "reload"}
