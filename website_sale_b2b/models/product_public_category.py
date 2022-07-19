from odoo import api, models


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    @api.multi
    def is_b2b(self):
        self.ensure_one()
        try:
            root_b2b_categ_id = self.env.ref(
                "website_sale_b2b.b2b_website_root_categ"
            ).id
        except ValueError:
            root_b2b_categ_id = None  # B2B category was removed
        if root_b2b_categ_id:
            root_category = self
            while root_category.parent_id:
                root_category = root_category.parent_id
            if root_category.id == root_b2b_categ_id:
                return True
        return False
