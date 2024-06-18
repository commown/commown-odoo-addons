from odoo.tests.common import SavepointCase


class StockPickingTC(SavepointCase):
    def test_name_get_with_context(self):
        loc1 = self.env["stock.location"].create(
            {
                "name": "Parent",
                "usage": "view",
                "partner_id": 1,
            }
        )

        loc2 = self.env["stock.location"].create(
            {
                "name": "Child",
                "usage": "internal",
                "partner_id": 1,
                "location_id": loc1.id,
            }
        )

        self.assertEqual(loc2.name_get()[0][1], "%s/%s" % (loc1.name, loc2.name))
        self.assertEqual(
            loc2.with_context({"short_location_name": True}).name_get()[0][1],
            loc2.name,
        )
