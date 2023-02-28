from odoo import fields, models


class ShareholderCategory(models.Model):
    _name = "commown_shareholder_register.category"
    _description = "Shareholder category"

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Category already exists!"),
        ("account_id_uniq", "unique (account_id)", "Account already used!"),
    ]

    name = fields.Char("Name", required=True)
    account_id = fields.Many2one("account.account", required=True)
    college_id = fields.Many2one("commown_shareholder_register.college", required=True)
    min_share_number = fields.Integer("Minimum share number", required=True)
