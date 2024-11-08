from odoo import api, fields, models


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    grade_id = fields.Many2one(
        "commown_grade.grade",
        string="Current grade",
        compute="_compute_grade_id",
        inverse="_inverse_grade_id",
        store=True,
        track_visibility="onchange",
    )

    grade_history_line_ids = fields.One2many(
        "commown_grade.grade_history_line",
        inverse_name="lot_id",
        store=True,
    )

    @api.depends("grade_history_line_ids.date")
    def _compute_grade_id(self):
        for lot in self:
            if lot.grade_history_line_ids:
                last_line = lot.grade_history_line_ids.sorted("date", reverse=True)[0]
                lot.grade_id = last_line.grade_id

    def _inverse_grade_id(self):
        for lot in self:
            if lot.grade_id:
                self.env["commown_grade.grade_history_line"].create(
                    {
                        "date": fields.Datetime.now(),
                        "grade_id": lot.grade_id.id,
                        "lot_id": lot.id,
                    }
                )
