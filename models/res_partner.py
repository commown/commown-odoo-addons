import logging

from odoo import models


_logger = logging.getLogger(__name__)


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
            _logger.debug(u"Partner %d (%s) has property_stock_customer=%s",
                          self.id, self.name, self.property_stock_customer.name)
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
                _logger.debug(u"Created location %d (%s) for partner %d (%s)",
                              location.id, location.name, self.id, self.name)
            self.update({'property_stock_customer': location.id})
            _logger.debug(u"Set location %d (%s) on partner %d (%s)",
                          location.id, location.name, self.id, self.name)
        _logger.debug(u"set_customer_location result %d (%s), partner %d (%s)",
                      self.property_stock_customer.id,
                      self.property_stock_customer.name, self.id, self.name)
        return self.property_stock_customer
