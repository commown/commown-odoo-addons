from datetime import date

from odoo import fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.product_rental.models.contract import NO_DATE

from .common import DeviceAsAServiceTC


class CrmLeadTC(DeviceAsAServiceTC):
    def test_actions_on_delivery_set_contract_start_date(self):
        leads = self.env["crm.lead"].search([("so_line_id.order_id", "=", self.so.id)])
        lead = leads.filtered("contract_id")[0]
        contract = lead.contract_id
        lead.send_email_on_delivery = False  # avoid setting-up email template

        # Check contract state before delivery
        self.assertFalse(contract.is_auto_pay)
        self.assertEqual(contract.date_start, NO_DATE)

        # Simulate delivery
        lead.delivery_date = date(2018, 1, 1)

        # Check results: contract started but is_auto_pay unchanged
        self.assertEqual(contract.date_start, date(2018, 1, 1))
        self.assertFalse(contract.is_auto_pay)

        # Simulate delivery again: happens when we send a new device
        # Contract start date should not change again!
        lead.delivery_date = date(2017, 1, 1)
        self.assertEqual(contract.date_start, date(2018, 1, 1))

    def test_picking_confirmation_on_delivery(self):
        "On delivery, picking must be automatically done"

        leads = self.env["crm.lead"].search([("so_line_id.order_id", "=", self.so.id)])
        self.assertEqual(len(leads), 3)
        lead = leads[0]
        lead.send_email_on_delivery = False  # avoid setting-up email
        lot = self.adjust_stock()  # have 1 product in stock

        # Should not be able to put the lead to a "go" column without a picking:
        stage = self.env["crm.stage"].create({"name": "GO [stock: check-has-picking]"})
        with self.assertRaises(ValidationError):
            with self.assertRaises(UserError) as err:
                lead.stage_id = stage.id
            self.assertEqual("Lead has no assigned picking.", err.exception.name)

        move_lines = lead.contract_id.send_devices(lot, {})
        self.assertEqual(move_lines.mapped("product_qty"), [1.0])
        self.assertEqual(move_lines.mapped("picking_id.state"), ["assigned"])

        # Now we should be able to move the lead
        lead.stage_id = stage.id
        self.assertEqual(lead.stage_id, stage)

        # Set delivery date to trigger the actions and check picking is now done
        lead.delivery_date = fields.Date.today()
        self.assertEqual(move_lines.mapped("picking_id.state"), ["done"])
