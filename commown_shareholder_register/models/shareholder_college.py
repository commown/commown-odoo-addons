from odoo import _, fields, models


class ShareholderCollege(models.Model):
    _name = "commown_shareholder_register.college"
    _description = "Shareholder college"

    _sql_constraints = [
        ("name_uniq", "unique (name)", "College already exists!"),
        ("rank_uniq", "unique (rank)", "Rank must be unique"),
    ]

    name = fields.Char("Name", required=True)
    rank = fields.Integer("Rank", required=True)
    category_ids = fields.One2many(
        "commown_shareholder_register.category",
        "college_id",
        string="Shareholder Categories",
    )

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, _("College %s") % record.name))
        return result
