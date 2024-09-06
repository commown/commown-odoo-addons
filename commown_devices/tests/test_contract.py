from odoo.tests.common import SavepointCase

from ..models.common import internal_picking


def create_product(env, name, tracked=False):
    if tracked:
        tracking = "serial"
    else:
        tracking = "none"

    template = env["product.template"].create(
        {
            "name": name,
            "type": "product",
            "tracking": tracking,
        }
    )
    return template.product_variant_id


class ContractTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.tracked_product = create_product(self.env, "Tracked product", tracked=True)

        lot = self.env["stock.production.lot"].create(
            {"name": "Super lot", "product_id": self.tracked_product.id}
        )

        self.untracked_product = create_product(
            self.env, "Untracked product", tracked=False
        )

        orig_location = self.env["stock.location"].create(
            {
                "name": "Origin location",
                "usage": "internal",
                "partner_id": 1,
            }
        )
        quants = self.env["stock.quant"].create(
            [
                {
                    "product_id": self.tracked_product.id,
                    "lot_id": lot.id,
                    "location_id": orig_location.id,
                    "quantity": 1,
                },
                {
                    "product_id": self.untracked_product.id,
                    "location_id": orig_location.id,
                    "quantity": 1,
                },
            ]
        )
        partner = self.env.ref("base.res_partner_2")
        self.contract = self.env["contract.contract"].create(
            {"name": "Test contract", "partner_id": partner.id}
        )
        dest_location = partner.get_or_create_customer_location()

        new_moves = internal_picking(
            [lot],
            {self.untracked_product: 1},
            orig_location,
            orig_location,
            dest_location,
            "origin",
        )
        self.contract.move_ids |= new_moves
        new_moves[0].picking_id.button_validate()
        self.all_move_lines = new_moves.mapped("move_line_ids")
        self.move_line_with_lot = self.all_move_lines.filtered("lot_id")

    def test_compute_lot_number(self):
        self.assertEqual(self.contract.lot_nb, 1)
        self.contract.update({"lot_ids": False})
        self.assertEqual(self.contract.lot_nb, 0)

    def test_compute_move_lines_view_ids(self):
        self.assertFalse(self.contract.show_all_view_move_lines)
        self.assertEqual(self.contract.move_line_view_ids, self.move_line_with_lot)

        self.contract.show_all_view_move_lines = True
        self.contract._compute_move_line_view_ids()

        self.assertEqual(self.contract.move_line_view_ids, self.all_move_lines)
