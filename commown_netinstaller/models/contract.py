from odoo import models


class Contract(models.Model):
    _inherit = "contract.contract"

    def netinstaller_specs(self):
        self.ensure_one()
        product = self.get_main_rental_line().sale_order_line_id.product_id
        return product.netinstaller_feature_typed_values()
