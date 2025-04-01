from odoo import _, api, models
from odoo.exceptions import UserError


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

    @api.multi
    def action_add_services_storable_products(self):
        "Action to add the storable products configured on sale-with-contract services"

        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Sale must be draft to use this action."))

        def _contract_sale_with_service(so_line):
            return (
                so_line.product_id.property_contract_template_id.stock_ownership
                == "customer"
            )

        for so_line in self.order_line.filtered(_contract_sale_with_service):
            storables = (
                so_line.product_id.primary_storable_variant_id
                | so_line.product_id.secondary_storable_variant_ids
            )
            for storable in storables:
                new_so_line = self.env["sale.order.line"].create(
                    {
                        "order_id": self.id,
                        "product_id": storable.id,
                        "product_uom_qty": so_line.product_uom_qty,
                    }
                )
                new_so_line.product_id_change()
