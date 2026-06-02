import datetime

from odoo.exceptions import UserError

from .common import BaseToCustomerPickingWizardTC


class WizardProjectTaskToCustomerPickingTC(BaseToCustomerPickingWizardTC):
    confirm_sale = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        service_tmpl = cls.service_product.product_tmpl_id
        my_project = cls.env["project.project"].create({"name": "my project"})
        my_project.picking_type_id = cls.env.ref("stock.picking_type_out")
        service_tmpl.followup_sales_project_id = my_project
        service_tmpl.property_contract_template_id.stock_ownership = "customer"

        cls.so.action_confirm()
        cls.task = my_project.task_ids[0]

        for_sale_stock = cls.env.ref("stock.stock_location_stock")
        for pt in cls.protective_screen, cls.usbc_cable:
            cls.adjust_stock_notracking(pt.product_variant_id, for_sale_stock)

    def test_picking(self):
        defaults, possibilities = self.prepare_wizard(self.task, "entity_id")
        scheduled_date = datetime.datetime(2020, 1, 10, 16, 2, 34)

        wizard = (
            self.env["project.task.to.customer.wizard"]
            .with_context(default_entity_id=self.task.id)
            .create({"entity_id": self.task.id, "scheduled_date": scheduled_date})
        )

        self.assertEqual(wizard.usage, "customer")

        picking = wizard.create_picking()

        # Check error on try to run action_to_customer_picking again
        with self.assertRaises(UserError) as err:
            self.task.action_to_customer_picking()
        self.assertIn("contract has already assigned picking", err.exception.args[0])

        # Check the result
        moves = picking.move_ids
        loc_new = self.env.ref("stock.stock_location_stock")

        self.assertEqual(moves, self.task.contract_id.move_ids)
        self.assertEqual(
            {m.product_id.name: m.state for m in picking.move_ids},
            {
                "Fairphone 3": "confirmed",
                "Protective Screen": "assigned",
                "Test USB-C Cable": "assigned",
            },
        )
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.move_type, "direct")
        self.assertEqual(picking.location_id, loc_new)

        self.assertEqual(len(moves), 3)
        loc_partner = self.so.partner_id.get_or_create_customer_location("customer")
        self.assertEqual(moves.mapped("location_id").ids, [loc_new.id])
        self.assertEqual(moves.mapped("location_dest_id"), loc_partner)

        self.assertFalse(moves.move_line_ids.lot_id)
