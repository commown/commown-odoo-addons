import logging

from odoo import models


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _customer_location_partner(self):
        "The location used for a partner is its commercial's except for commown"
        self.ensure_one()

        if (self.commercial_partner_id != self
                and self.commercial_partner_id.id != 1):
            return self.commercial_partner_id
        else:
            return self

    def get_customer_location(self):
        "Search for the oldest current partner's location and return it"

        partner = self._customer_location_partner()
        if partner != self:
            return partner.get_customer_location()

        parent_location = self.env.ref('stock.stock_location_customers')

        return self.env["stock.location"].search([
            ("partner_id", "=", self.id),
            ("usage", "=", "customer"),
            ("location_id", "=", parent_location.id),
        ], order="id ASC", limit=1)

    def get_or_create_customer_location(self):
        """ Return current partner's location, creating it if it does not exist

        The created location is a child of standard location for all
        customers, with usage 'customer' and same name as the partner.
        """

        location = self.get_customer_location()
        if location:
            return location

        partner = self._customer_location_partner()
        if partner != self:
            return partner.get_or_create_customer_location()

        parent_location = self.env.ref('stock.stock_location_customers')

        _logger.debug(u"Partner %d (%s) has no customer location yet,"
                      " creating one", self.id, self.name)
        return self.env['stock.location'].sudo().create({
            'name': self.name,
            'usage': 'customer',
            'partner_id': self.id,
            'location_id': parent_location.id,
        })
