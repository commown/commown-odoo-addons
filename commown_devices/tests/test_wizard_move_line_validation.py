from odoo.tests.common import SavepointCase

from ..models.common import internal_picking
from .common import create_lot_and_quant


class WizardMoveLineValidationTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        self.contract = self.env["contract.contract"].create(
            {"name": "Contract", "partner_id": self.partner.id}
        )
        self.stock_location = self.env.ref("stock.stock_location_stock")
        product = self.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        self.lot = create_lot_and_quant(self.env, "lot1", product, self.stock_location)

        self.move = internal_picking(
            self.lot,
            {},
            None,
            self.stock_location,
            self.partner.get_or_create_customer_location(),
            "origin",
        )
        self.move.update({"contract_id": self.contract})

    def test_move_line_validation_wizard(self):
        wizard = self.env["move.line.validation.wizard"].create(
            {"move_line_id": self.move.move_line_ids[0].id}
        )

        self.assertIn(
            "%s - %s"
            % (self.move.product_id.name, self.move.date.strftime("%d/%m/%y")),
            wizard.message,
        )

        wizard.action_validate()
        self.assertEquals(self.move.picking_id.state, "done")
