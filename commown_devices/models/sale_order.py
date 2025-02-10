from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """Serial-tracked products must be sent to a customer-specific location
        so that we know which devices the customer has and we may get back when EOL.
        """

        def _is_serial(product):
            return product.tracking == "serial"

        if self.order_line.mapped("product_id").filtered(_is_serial):
            # Get or create partner's for-sale location...
            dest_partner = self.partner_shipping_id or self.partner_id
            dest_loc = dest_partner.get_or_create_customer_location("customer")
            # ... and set it on sale's shipping partner:
            dest_partner.property_stock_customer = dest_loc

        return super().action_confirm()
