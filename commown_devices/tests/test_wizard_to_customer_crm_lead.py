import datetime
import json

from odoo.exceptions import UserError
from odoo.fields import Command

from .common import BaseToCustomerPickingWizardTC


class WizardCrmLeadPickingTC(BaseToCustomerPickingWizardTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so.action_confirm()
        cls.lead = cls.env["crm.lead"].search(
            [("so_line_id", "=", cls.so.order_line.ids[0])]
        )[0]
        cls.adjust_stock(cls.fp3_plus_storable_color1, serial="test-fp3+-1")
        cls.adjust_stock(cls.fp3_plus_storable_color1, serial="test-fp3+-2")

    def test_find_nonserial_product_orig_location(self):
        lead = self.lead

        loc_repackaged_modules = self.env.ref(
            "commown_devices.stock_repackaged_modules_and_accessories"
        )

        defaults, possibilities = self.prepare_wizard(lead, "entity_id")

        chan = json.dumps(self.env.user.notify_info_channel_name)
        notifs = self.env["bus.bus"].search([("channel", "=", chan)])
        self.assertEqual(
            {"Not in stock: %s" % self.protective_screen.name},
            {json.loads(n["message"])["message"] for n in notifs},
        )

        self.adjust_stock_notracking(
            self.protective_screen.product_variant_id, self.loc_new_untracked
        )
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = (
            self.env["crm.lead.to.customer.wizard"]
            .with_context(default_entity_id=lead.id)
            .create(
                {
                    "entity_id": lead.id,
                    "date": date,
                }
            )
        )
        self.assertEqual(
            wizard._compute_products_locations(),
            "%s: %s, %s"
            % (
                self.loc_new_untracked.name,
                self.protective_screen.name,
                self.usbc_cable.name,
            ),
        )

        self.adjust_stock_notracking(
            self.protective_screen.product_variant_id, loc_repackaged_modules
        )

        self.assertEqual(
            wizard._compute_products_locations(),
            "%s: %s\n%s: %s"
            % (
                loc_repackaged_modules.name,
                self.protective_screen.name,
                self.loc_new_untracked.name,
                self.usbc_cable.name,
            ),
        )

        wizard.prioritize_repackaged = False
        self.assertEqual(
            wizard._compute_products_locations(),
            "%s: %s, %s"
            % (
                self.loc_new_untracked.name,
                self.protective_screen.name,
                self.usbc_cable.name,
            ),
        )

    def test_ui(self):
        lead = self.lead

        self.adjust_stock_notracking(
            self.protective_screen.product_variant_id, self.loc_new_untracked
        )

        # Check action
        action = lead.action_to_customer_picking()
        self.assertEqual(action.get("res_model"), "crm.lead.to.customer.wizard")
        self.assertEqual(action.get("context").get("default_entity_id"), lead.id)

        # Get values to test
        defaults, possibilities = self.prepare_wizard(lead, "entity_id")

        # Check defaults

        self.assertEqual(defaults["entity_id"], lead.id)
        all_products_ids = [
            cmd[1] for cmd in defaults["all_products"] if cmd[0] == Command.UPDATE
        ]
        self.assertEqual(
            sorted(all_products_ids),
            sorted(
                [
                    self.fp3_plus_storable_color1.id,
                    self.usbc_cable.product_variant_id.id,
                    self.protective_screen.product_variant_id.id,
                ]
            ),
        )

        # Check domains
        self.assertEqual(
            possibilities["lot_ids"].mapped("name"),
            ["test-fp3+-1", "test-fp3+-2"],
        )

    def test_picking(self):
        # Prepare test data
        lead = self.lead

        self.adjust_stock_notracking(
            self.protective_screen.product_variant_id, self.loc_new_untracked
        )

        defaults, possibilities = self.prepare_wizard(lead, "entity_id")
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = (
            self.env["crm.lead.to.customer.wizard"]
            .with_context(default_entity_id=lead.id)
            .create(
                {
                    "entity_id": lead.id,
                    "date": date,
                }
            )
        )
        lot = possibilities["lot_ids"][0]
        wizard.lot_ids = lot

        self.assertEqual(wizard.usage, "internal")

        moves = wizard.create_picking()

        # Check error on try to run action_to_customer_picking again
        with self.assertRaises(UserError) as err:
            lead.action_to_customer_picking()
        self.assertIn("contract has already assigned picking", err.exception.args[0])

        # Check the result
        picking = moves.mapped("picking_id")
        loc_new = self.env.ref("commown_devices.stock_location_available_for_rent")

        self.assertEqual(moves, lead.contract_id.move_ids)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.move_type, "direct")
        self.assertEqual(picking.location_id, loc_new)

        moves = picking.move_ids
        self.assertEqual(len(moves), 3)
        loc_partner = self.so.partner_id.get_or_create_customer_location("internal")
        self.assertEqual(
            sorted(moves.mapped("location_id").ids),
            sorted([self.location_fp3_new.id, self.loc_new_untracked.id]),
        )
        self.assertEqual(moves.mapped("location_dest_id"), loc_partner)

        self.assertEqual(moves.mapped("move_line_ids.lot_id.name"), [lot.name])
