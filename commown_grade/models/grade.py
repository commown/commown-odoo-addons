from odoo import fields, models


class Grade(models.Model):
    _name = "commown_grade.grade"
    _description = "Grade"

    _sql_constraints = [
        ("name_uniq", "unique (name)", "The grade name must be unique"),
    ]

    _order = "name"

    name = fields.Char(
        required=True,
        translate=True,
    )

    description = fields.Char(
        translate=True,
    )
