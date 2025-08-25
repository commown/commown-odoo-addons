from odoo import api, models


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.multi
    def netinstaller_feature_values(self):
        self.ensure_one()
        product = self.get_main_rental_line().sale_order_line_id.product_id
        return product.netinstaller_feature_values()
