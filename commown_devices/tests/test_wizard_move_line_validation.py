from odoo.tests.common import TransactionCase

from ..models.common import internal_picking
from .common import create_lot_and_quant


class WizardMoveLineValidationTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.contract = cls.env["contract.contract"].create(
            {"name": "Contract", "partner_id": cls.partner.id}
        )
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        product = cls.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        cls.lot = create_lot_and_quant(cls.env, "lot1", product, cls.stock_location)

        cls.move = internal_picking(
            cls.lot,
            {},
            None,
            cls.stock_location,
            cls.partner.get_or_create_customer_location(cls.contract.stock_ownership),
            False,
        )
        cls.move.update({"contract_id": cls.contract})

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
        self.assertEqual(self.move.picking_id.state, "done")
