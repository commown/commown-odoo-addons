import json

from odoo.addons.commown_devices.tests.common import BaseWizardToEmployeeMixin

from .common import RentalFeesTC


class WizardToEmployeeTC(BaseWizardToEmployeeMixin, RentalFeesTC):
    def create_po_and_picking(self, *args, **kwargs):
        "Override to set default receipt picking destination to available for rent"
        rent_loc = self.env.ref("commown_devices.stock_location_available_for_rent")
        loc = self.env["stock.location"].create(
            {"name": "Test loc", "usage": "internal", "location_id": rent_loc.id},
        )

        self.env.ref("stock.picking_type_in").default_location_dest_id = loc.id
        return super().create_po_and_picking(*args, **kwargs)

    def get_wizard(self, **kwargs):
        lot = self.env["stock.production.lot"].search([("name", "=", "N/S 1")])
        kwargs.setdefault("lot_id", lot.id)
        return super().get_wizard(**kwargs)

    def get_infos(self, old_infos=None):
        name = json.dumps(self.env.user.notify_info_channel_name)
        objs = self.env["bus.bus"].search([("channel", "=", name)], order="id")
        msgs = [json.loads(m)["message"] for m in objs.mapped("message")]
        return msgs[len(old_infos or ()) :]

    def test_give_concerned_by_fees_device_to_employee(self):
        "Device given to an employee must be excluded from fees if concerned"

        self.assertNotIn("N/S 1", self.fees_def.excluded_devices.mapped("device.name"))

        old_infos = self.get_infos()
        self.get_wizard().execute()
        new_infos = self.get_infos(old_infos)

        self.assertIn("N/S 1", self.fees_def.excluded_devices.mapped("device.name"))

        self.assertEqual(
            new_infos,
            ["Device N/S 1 excluded from fees in def id %d" % self.fees_def.id],
        )

    def test_give_already_excluded_from_fees_device_to_employee(self):
        "User giving a fees-excluded device to an employee is informed"

        lot = self.env["stock.production.lot"].search([("name", "=", "N/S 1")])
        self.env["rental_fees.excluded_device"].create(
            {"fees_definition_id": self.fees_def.id, "device": lot.id, "reason": "test"}
        )

        old_infos = self.get_infos()
        self.get_wizard().execute()
        new_infos = self.get_infos(old_infos)

        self.assertEqual(
            new_infos,
            [
                "Device N/S 1 was already excluded from fees (in fees def id %d)"
                % self.fees_def.id
            ],
        )

    def test_give_not_concerned_by_fees_device_to_employee(self):
        "User giving a device to an employee is informed when it's not subject to fees"

        self.fees_def.order_ids = False

        old_infos = self.get_infos()
        self.get_wizard().execute()
        new_infos = self.get_infos(old_infos)

        self.assertEqual(new_infos, ["Device N/S 1 is not subject to fees as of now."])
