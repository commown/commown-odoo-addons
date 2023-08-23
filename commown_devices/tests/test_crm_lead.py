from odoo import fields
from odoo.exceptions import UserError, ValidationError

from .common import DeviceAsAServiceTC


class CrmLeadTC(DeviceAsAServiceTC):
    def test_picking_confirmation_on_delivery(self):
        "On delivery, picking must be automatically done"

        leads = self.env["crm.lead"].search(
            [
                ("so_line_id.order_id", "=", self.so.id),
            ]
        )
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

        picking = lead.contract_id.send_devices([lot], {})
        self.assertEqual(picking.mapped("move_lines.product_qty"), [1.0])
        self.assertEqual(picking.state, "assigned")

        # Set delivery date to trigger the actions and check picking is now done
        lead.delivery_date = fields.Date.today()
        self.assertEqual(picking.state, "done")
