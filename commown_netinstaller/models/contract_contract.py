from odoo import api, models


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.multi
    def netinstaller_feature_values(self):
        self.ensure_one()
        product = self.get_main_rental_line().sale_order_line_id.product_id
        result = {}
        for fvalue in product.cumulated_netinstaller_feature_value_ids:
            assert fvalue.feature_id.name not in result
            result[fvalue.feature_id.name] = fvalue.value
        return result
