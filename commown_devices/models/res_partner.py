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

        if (self.commercial_partner_id != self
                and self.commercial_partner_id.id != 1):
            return self.commercial_partner_id.set_customer_location()

        parent_location = self.env.ref('stock.stock_location_customers')

        location = self.env["stock.location"].search([
            ("partner_id", "=", self.id),
            ("usage", "=", "customer"),
            ("location_id", "=", parent_location.id),
        ], order="id ASC", limit=1)

        if not location:
            _logger.debug(u"Partner %d (%s) has no customer location yet,"
                          " creating one", self.id, self.name)
            location = self.env['stock.location'].create({
                'name': self.name,
                'usage': 'customer',
                'partner_id': self.id,
                'location_id': parent_location.id,
            })

        _logger.debug("Customer location of partner %d (%s) is %d",
                      self.id, self.name, location.id)
        return location
