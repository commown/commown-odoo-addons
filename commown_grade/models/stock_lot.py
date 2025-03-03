from odoo import _, api, fields, models


class StockProductionLot(models.Model):
    _inherit = "stock.lot"

    grade_id = fields.Many2one(
        "commown_grade.grade",
        string="Current grade",
        compute="_compute_grade_id",
        inverse="_inverse_grade_id",
        store=True,
        tracking=True,
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

    def _compute_grade_history_line_ids(self):
        for lot in self:
            lot.grade_history_line_ids = lot.env[
                "commown_grade.grade_history_line"
            ].search(
                [("lot_id", "=", lot.id)],
                order="date",
            )

    @api.onchange("grade_id")
    def _onchange_grade_id(self):
        if self.grade_history_line_ids and self.grade_id:
            # Use history line instead of _origin to get old grade so we can notify even
            # when grade was empty
            old_grade = self.grade_history_line_ids.sorted("date", reverse=True)[
                0
            ].grade_id
            if self.grade_id.name < old_grade.name:
                self.env.user.notify_info(
                    message=_(
                        "New grade is better than the last known grade, are you sure of"
                        " this change?"
                    ),
                    title=_("Grade Improvement"),
                    sticky=False,
                )
