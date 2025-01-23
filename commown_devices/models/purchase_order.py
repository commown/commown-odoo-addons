from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    default_product_grade = fields.Many2one(
        "commown_grade.grade",
        required=False,
        default=lambda self: self.env["commown_grade.grade"].search([], limit=1).id,
    )
