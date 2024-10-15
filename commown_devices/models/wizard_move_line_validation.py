from odoo import api, fields, models


class MoveLineValidationWizard(models.TransientModel):
    _name = "move.line.validation.wizard"
    _description = "Ask confirmation for move line action validate linked picking"

    move_line_id = fields.Many2one(
        "stock.move.line",
        string="Move line id",
        required=True,
    )

    message = fields.Html(
        compute="_compute_display_message",
        store=False,
    )

    @api.onchange("move_line_id")
    def _compute_display_message(self):
        message = "Several unvalidated moves. Are you sure you want to validate this one: <b>%s - %s</b> ?"
        self.message = message % (
            self.move_line_id.product_id.name,
            self.move_line_id.date.strftime("%d/%m/%y"),
        )

    def action_validate(self):
        self.move_line_id.move_id.picking_id.button_validate()
