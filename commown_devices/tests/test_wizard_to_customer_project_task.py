import datetime

from odoo.exceptions import UserError

from .common import BaseToCustomerPickingWizardTC


class WizardProjectTaskToCustomerPickingTC(BaseToCustomerPickingWizardTC):
    confirm_sale = False

    def setUp(self):
        super().setUp()

        service_tmpl = self.service_product.product_tmpl_id
        my_project = self.env["project.project"].create({"name": "my project"})
        service_tmpl.followup_sales_project_id = my_project
        service_tmpl.property_contract_template_id.stock_ownership = "customer"

        self.so.action_confirm()
        self.task = my_project.task_ids[0]

        for_sale_stock = self.env.ref("stock.stock_location_stock")
        for pt in self.protective_screen, self.usbc_cable:
            self.adjust_stock_notracking(pt.product_variant_id, for_sale_stock)

        _pt = self.fp3_plus_storable_color1
        for serial in ("test-fp3+-1", "test-fp3+-2"):
            self.adjust_stock(_pt, serial=serial, location=for_sale_stock)

    def test_picking(self):

        defaults, possibilities = self.prepare_wizard(self.task, "entity_id")
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)

        wizard = (
            self.env["project.task.to.customer.wizard"]
            .with_context({"default_entity_id": self.task.id})
            .create({"entity_id": self.task.id, "date": date})
        )
        lot = possibilities["lot_ids"][0]
        wizard.lot_ids = lot

        self.assertEqual(wizard.usage, "customer")

        moves = wizard.create_picking()

        # Check error on try to run action_to_customer_picking again
        with self.assertRaises(UserError) as err:
            self.task.action_to_customer_picking()
        self.assertIn("contract has already assigned picking", err.exception.name)

        # Check the result
        picking = moves.mapped("picking_id")
        loc_new = self.env.ref("stock.stock_location_stock")

        self.assertEqual(moves, self.task.contract_id.move_ids)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.move_type, "direct")
        self.assertEqual(picking.location_id, loc_new)

        moves = picking.move_lines
        self.assertEqual(len(moves), 3)
        loc_partner = self.so.partner_id.get_or_create_customer_location("customer")
        self.assertEqual(moves.mapped("location_id").ids, [loc_new.id])
        self.assertEqual(moves.mapped("location_dest_id"), loc_partner)

        self.assertEqual(moves.mapped("move_line_ids.lot_id.name"), [lot.name])
