from odoo import fields

from .common import DeviceAsAServiceTC


class CrmLeadTC(DeviceAsAServiceTC):

    def test_picking_confirmation_on_delivery(self):
        "On delivery, picking must be automatically done"

        lead = self.env['crm.lead'].search([
            ('so_line_id.order_id', '=', self.so.id),
        ]).ensure_one()
        lead.send_email_on_delivery = False  # avoid setting-up email
        self.adjust_stock()  # have 1 product in stock
        picking = lead.contract_id.send_all_picking()
        picking.pack_operation_ids.pack_lot_ids.do_plus()
        self.assertEqual(picking.state, 'assigned')

        # Set delivery date to trigger the actions and check picking is now done
        lead.delivery_date = fields.Date.today()
        self.assertEqual(picking.state, 'done')
