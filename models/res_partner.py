from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def set_customer_location(self):
        """Set property_stock_customer to a dedicated location and return it

        The dedicated location is a child of standard location for all
        customers.
        """

        customer_location = self.env.ref('stock.stock_location_customers')

        if self.property_stock_customer == customer_location:
            location = self.env['stock.location'].create({
                'name': self.name,
                'usage': 'internal',
                'partner_id': self.id,
                'location_id': customer_location.id,
            })
            self.update({'property_stock_customer': location.id})

        return self.property_stock_customer
