from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _set_location(self, usage, parent_xml_id, attr):
        parent_location = self.env.ref(parent_xml_id)

        if getattr(self, attr) == parent_location:
            location = self.env['stock.location'].create({
                'name': self.name,
                'usage': usage,
                'partner_id': self.id,
                'location_id': parent_location.id,
            })
            self.update({attr: location.id})

        return getattr(self, attr)

    def set_supplier_location(self):
        """Set property_stock_supplier to a dedicated location and return it

        The dedicated location is a child of standard location for all
        suppliers.
        """
        return self._set_location('supplier',
                                  'stock.stock_location_suppliers',
                                  'property_stock_supplier')


    def set_customer_location(self):
        """Set property_stock_customer to a dedicated location and return it

        The dedicated location is a child of standard location for all
        customers.
        """

        return self._set_location('internal',
                                  'stock.stock_location_customers',
                                  'property_stock_customer')
