from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def is_b2b(self):
        self.ensure_one()
        for category in self.public_categ_ids:
            if category.is_b2b():
                return True
        return False
