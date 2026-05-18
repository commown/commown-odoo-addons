from odoo import models


class Contract(models.Model):
    _inherit = "contract.contract"

    def netinstaller_feature_values(self):
        self.ensure_one()
        product = self.get_main_rental_line().sale_order_line_id.product_id
        result = {}
        for fvalue in product.cumulated_netinstaller_feature_value_ids:
            value = fvalue.typed_value()
            if fvalue.feature_id.name in result:
                result[fvalue.feature_id.name] += value
            else:
                result[fvalue.feature_id.name] = value
        return result
