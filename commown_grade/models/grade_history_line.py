from odoo import fields, models


class GradeHistoryLine(models.Model):
    _name = "commown_grade.grade_history_line"
    _description = "Store the grade a lot had at one given date"

    _order = "lot_id, date desc"

    date = fields.Datetime(default=fields.Datetime.now, required=True)

    grade_id = fields.Many2one(
        "commown_grade.grade",
        string="Grade",
        index=True,
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        index=True,
        required=True,
    )

    product_id = fields.Many2one(
        related="lot_id.product_id",
        index=True,
        store=True,
    )
