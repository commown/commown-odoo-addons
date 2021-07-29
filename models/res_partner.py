from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def set_customer_location(self):
        """Set property_stock_customer to a dedicated location and return it

        The dedicated location is a child of standard location for all
        customers.
        """

        parent_location = self.env.ref('stock.stock_location_customers')

        if self.property_stock_customer == parent_location:
            # Handle B2B: do not create a location for each employee
            # Special case: our own employees!
            if (self.commercial_partner_id != self
                    and self.commercial_partner_id.id != 1):
                location = self.commercial_partner_id.set_customer_location()

            else:
                location = self.env['stock.location'].create({
                    'name': self.name,
                    'usage': 'customer',
                    'partner_id': self.id,
                    'location_id': parent_location.id,
                })
            self.update({'property_stock_customer': location.id})

        return self.property_stock_customer
