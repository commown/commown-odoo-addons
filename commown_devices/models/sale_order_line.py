from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self):
        "Deactivate procurement/picking logic when the sale contains a contract"

        if self.mapped("order_id.order_line.product_id.property_contract_template_id"):
            return True
        else:
            return super()._action_launch_stock_rule()
