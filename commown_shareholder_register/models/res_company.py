from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    nominal_share_amount = fields.Float("Nominal share amount")
