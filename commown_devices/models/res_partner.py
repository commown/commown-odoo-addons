import logging

import psycopg2

from odoo import api, models
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _customer_location_partner(self):
        "The location used for a partner is its commercial's except for commown"
        self.ensure_one()

        if self.commercial_partner_id != self and self.commercial_partner_id.id != 1:
            return self.commercial_partner_id
        else:
            return self

    def get_customer_location(self, limit=1):
        "Search for the oldest current partner's location and return it"

        partner = self._customer_location_partner()
        if partner != self:
            return partner.get_customer_location()

        parent_location = self.env.ref("stock.stock_location_customers")

        return self.env["stock.location"].search(
            [
                ("partner_id", "=", self.id),
                ("usage", "=", "internal"),
                ("location_id", "=", parent_location.id),
            ],
            order="id ASC",
            limit=limit,
        )

    def get_or_create_customer_location(self):
        """Return current partner's location, creating it if it does not exist

        The created location is a child of standard location for all
        customers, with usage 'customer' and same name as the partner.
        """

        location = self.get_customer_location()
        if location:
            return location

        partner = self._customer_location_partner()
        if partner != self:
            return partner.get_or_create_customer_location()

        parent_location = self.env.ref("stock.stock_location_customers")

        _logger.debug(
            "Partner %d (%s) has no customer location yet," " creating one",
            self.id,
            self.name,
        )
        return (
            self.env["stock.location"]
            .sudo()
            .create(
                {
                    "name": self.name,
                    "usage": "internal",
                    "partner_id": self.id,
                    "location_id": parent_location.id,
                }
            )
        )

    def _get_fk_on(self, table):
        """Copied from MergePartnerAutomatic in odoo code base

        Return a list of many2one relation with the given table.
        :param table : the name of the sql table to return relations
        :returns a list of tuple 'table name', 'column name'.
        """
        query = """
            SELECT cl1.relname as table, att1.attname as column
            FROM pg_constraint as con,
                 pg_class as cl1,
                 pg_class as cl2,
                 pg_attribute as att1,
                 pg_attribute as att2
            WHERE con.conrelid = cl1.oid
                AND con.confrelid = cl2.oid
                AND array_lower(con.conkey, 1) = 1
                AND con.conkey[1] = att1.attnum
                AND att1.attrelid = cl1.oid
                AND cl2.relname = %s
                AND att2.attname = 'id'
                AND array_lower(con.confkey, 1) = 1
                AND con.confkey[1] = att2.attnum
                AND att2.attrelid = cl2.oid
                AND con.contype = 'f'
        """
        self.env.cr.execute(query, (table,))
        return self.env.cr.fetchall()

    @api.model
    def _update_foreign_keys(self, src_locations, dst_location):
        """Update all foreign keys valued a source location to the destination location
        Inspired from MergePartnerAutomatic in odoo code base.
        """

        _logger.debug(
            "_update_foreign_keys for dst_location: %s and src_locations: %s",
            dst_location.id,
            src_locations.ids,
        )

        for table, column in self._get_fk_on("stock_location"):
            query_ctx = {"table": table, "column": column}
            try:
                with mute_logger("odoo.sql_db"), self.env.cr.savepoint():
                    query = (
                        'UPDATE "%(table)s" SET "%(column)s" = %%s'
                        ' WHERE "%(column)s" IN %%s' % query_ctx
                    )
                    self.env.cr.execute(
                        query, (dst_location.id, tuple(src_locations.ids))
                    )

            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent partner_id is useless, better
                # delete it
                query = 'DELETE FROM "%(table)s" WHERE "%(column)s" IN %%s' % query_ctx
                self.env.cr.execute(query, (tuple(src_locations.ids),))

    def merge_stock_locations(self):
        "Merge partner locations if he has several, keeping the oldest one"
        self.ensure_one()
        partner_locations = self.get_customer_location(limit=None)
        if len(partner_locations) > 1:
            dst_location, src_locations = partner_locations[0], partner_locations[1:]
            self._update_foreign_keys(src_locations, dst_location)
            src_locations.unlink()

    @api.multi
    def write(self, vals):
        "Handle individual > professional status change regarding stock location"

        to_change_customer_loc = (
            "parent_id" in vals
            and self.commercial_partner_id == self
            and self.get_customer_location()
        )

        result = super().write(vals)

        if to_change_customer_loc and self.commercial_partner_id != self:
            new_loc = self.get_or_create_customer_location()
            self._update_foreign_keys(to_change_customer_loc, new_loc)
            to_change_customer_loc.unlink()

        return result


class MergePartnerAutomatic(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        "Also merge partner stock locations"
        result = super()._merge(
            partner_ids,
            dst_partner=dst_partner,
            extra_checks=extra_checks,
        )

        dst_partner = dst_partner or partner_ids.exist()
        if len(dst_partner) == 1:
            dst_partner.merge_stock_locations()

        return result
