from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def name_get(self):
        if not self.env.context.get("short_location_name", False):
            return super().name_get()

        ret_list = []
        for location in self:
            ret_list.append((location.id, location.name))
        return ret_list

    def has_partner_child_of(self, loc):
        """Return if current location is owned by a child of given location's partner

        We rely on the child_of relation of partners to avoid data duplication between
        the partner and location child_of hierarchies.
        """
        return bool(
            self.env["res.partner"]
            .with_context(active_test=False)
            .search_count(
                [("id", "=", self.partner_id.id), ("id", "child_of", loc.partner_id.id)]
            )
        )
