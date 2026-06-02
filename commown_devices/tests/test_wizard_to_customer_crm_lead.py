import datetime

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
        cls.lead.team_id.carrier_account_id = cls.env.ref(
            "commown_shipping.carrier-account-colissimo-std-account"
        )

    def test_ui(self):
        lead = self.lead

        # Check action
        action = lead.action_to_customer_picking()
        self.assertEqual(action.get("res_model"), "crm.lead.to.customer.wizard")
        self.assertEqual(action.get("context").get("default_entity_id"), lead.id)

        # Get values to test
        defaults, possibilities = self.prepare_wizard(lead, "entity_id")

        # Check defaults

        self.assertEqual(defaults["entity_id"], lead.id)
        products = [cmd[1] for cmd in defaults["products"] if cmd[0] == Command.UPDATE]
        self.assertEqual(
            sorted(products),
            sorted(
                [
                    self.fp3_plus_storable_color1.id,
                    self.usbc_cable.product_variant_id.id,
                    self.protective_screen.product_variant_id.id,
                ]
            ),
        )
        self.assertEqual(
            defaults["carrier_account_id"], lead.team_id.carrier_account_id.id
        )
        self.assertEqual(defaults["usage"], "internal")

        # Check domains
        self.assertEqual(
            set(possibilities["products"].mapped("product_tmpl_id.type")),
            {"product"},
        )

    def test_picking(self):
        # Prepare test data
        lead = self.lead

        self.prepare_wizard(lead, "entity_id")
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = (
            self.env["crm.lead.to.customer.wizard"]
            .with_context(default_entity_id=lead.id)
            .create(
                {
                    "entity_id": lead.id,
                    "scheduled_date": date,
                    "os": "android",
                }
            )
        )
        self.assertEqual(wizard.usage, "internal")

        picking = wizard.create_picking()

        # Check error on try to run action_to_customer_picking again
        with self.assertRaises(UserError) as err:
            lead.action_to_customer_picking()
        self.assertIn("contract has already assigned picking", err.exception.args[0])

        # Check the result
        loc_new = self.env.ref("commown_devices.stock_location_available_for_rent")

        moves = picking.move_ids
        self.assertEqual(moves, lead.contract_id.move_ids)
        self.assertEqual(picking.state, "confirmed")
        self.assertEqual(picking.move_type, "direct")
        self.assertEqual(picking.location_id, loc_new)

        moves = picking.move_ids
        self.assertEqual(len(moves), 3)
        loc_partner = self.so.partner_id.get_or_create_customer_location("internal")
        self.assertEqual(moves.mapped("location_dest_id"), loc_partner)
        self.assertFalse(moves.mapped("move_line_ids.lot_id"))
