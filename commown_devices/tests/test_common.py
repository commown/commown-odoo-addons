from odoo.tests.common import SavepointCase

from ..models.common import first_common_location


def create_stock_location(self, name, parent=None):
    return self.env["stock.location"].create(
        {
            "name": name,
            "usage": "internal",
            "partner_id": 1,
            "location_id": parent.id if parent != None else False,
        }
    )


class CommonFunctionsTC(SavepointCase):
    """This class is used to test the functions of models/commown
    that are not fully tested in other tests files.
    """

    def setUp(self, *args, **kwargs):
        super(CommonFunctionsTC, self).setUp(*args, **kwargs)

        self.loc_1 = create_stock_location(self, "Loc-1")
        self.loc_1_1 = create_stock_location(self, "Loc-1-1", self.loc_1)
        self.loc_1_2 = create_stock_location(self, "Loc_1_2", self.loc_1)
        self.loc_1_2_1 = create_stock_location(self, "Loc_1_2_1", self.loc_1_2)
        self.loc_1_2_2 = create_stock_location(self, "Loc-1-2-2", self.loc_1_2)
        self.loc_4 = create_stock_location(self, "Loc-4")

    def test_first_common_location(self):
        self.assertEqual(
            first_common_location([self.loc_1_2_1]),
            self.loc_1_2_1,
        )
        self.assertEqual(
            first_common_location([self.loc_1_2_1, self.loc_1_2_2]),
            self.loc_1_2,
        )
        self.assertEqual(
            first_common_location([self.loc_1_2_1, self.loc_1_2_2, self.loc_1_1]),
            self.loc_1,
        )
        self.assertEqual(
            first_common_location(
                [self.loc_1_2_1, self.loc_1_2_2, self.loc_1_1, self.loc_1]
            ),
            self.loc_1,
        )
        self.assertEqual(
            first_common_location(
                [self.loc_1_2_1, self.loc_1_2_2, self.loc_1_1, self.loc_1, self.loc_4]
            ),
            self.env["stock.location"],
        )
