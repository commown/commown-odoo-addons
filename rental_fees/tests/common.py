from datetime import date, datetime

from odoo.addons.commown_devices.tests.common import DeviceAsAServiceTC


def _set_date(entity, value, attr_name):
    setattr(entity.sudo(), attr_name, value)
    sql = "UPDATE %s SET %s=%%s WHERE id=%%s" % (
        entity._name.replace(".", "_"),
        attr_name,
    )
    entity.env.cr.execute(sql, (str(value), entity.id))


class RentalFeesTC(DeviceAsAServiceTC):
    def setUp(self):
        super().setUp()
        self.po = self.create_po_and_picking(("N/S 1", "N/S 2", "N/S 3"))
        self.fees_def = self.env["rental_fees.definition"].create(
            {
                "name": "Test fees_def",
                "partner_id": self.po.partner_id.id,
                "product_template_id": self.storable_product.id,
                "order_ids": [(6, 0, self.po.ids)],
                "agreed_to_std_price_ratio": 0.4,
                "penalty_period_duration": 1,
                "no_rental_duration": 6,
            }
        )
        self.env["rental_fees.definition_line"].create(
            {
                "fees_definition_id": self.fees_def.id,
                "sequence": 1,
                "duration_value": 2,
                "duration_unit": "months",
                "fees_type": "proportional",
                "monthly_fees": 0.1,
            }
        )
        self.env["rental_fees.definition_line"].create(
            {
                "fees_definition_id": self.fees_def.id,
                "sequence": 2,
                "duration_value": 3,
                "duration_unit": "months",
                "fees_type": "proportional",
                "monthly_fees": 0.5,
            }
        )
        self.env["rental_fees.definition_line"].create(
            {
                "fees_definition_id": self.fees_def.id,
                "sequence": 100,
                "duration_value": False,
                "duration_unit": "months",
                "fees_type": "proportional",
                "monthly_fees": 0.05,
            }
        )

    def create_po_and_picking(
        self,
        serials,
        partner=None,
        product=None,
        price_unit=200.0,
    ):
        "Return a purchase order with a done picking, generating given serials"
        partner = partner or self.env.ref("base.res_partner_1")
        product = product or self.storable_product.product_variant_id

        po = self.env["purchase.order"].create({"partner_id": partner.id})
        po.order_line |= self.env["purchase.order.line"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_qty": len(serials),
                "product_uom": product.uom_id.id,
                "price_unit": price_unit,
                "date_planned": date(2021, 1, 1),
                "order_id": po.id,
            }
        )
        po.button_confirm()

        move_lines = po.picking_ids.move_lines.move_line_ids
        for lot_name, move_line in zip(serials, move_lines):
            move_line.update({"lot_name": lot_name, "qty_done": 1})
        po.picking_ids.button_validate()

        for move in po.picking_ids.move_lines:
            _set_date(move, po.date_planned, "date")
            for ml in move.move_line_ids:
                _set_date(ml, po.date_planned, "date")

        return po

    def current_quant(self, device):
        return (
            self.env["stock.quant"]
            .search([("lot_id", "=", device.id), ("quantity", ">", 0.0)])
            .ensure_one()
        )

    def scrap_device(self, device, date):
        "Simulate device scrapping at given (enforced) date"
        scrap_loc = self.env.ref("stock.stock_location_scrapped")
        scrap = self.env["stock.scrap"].create(
            {
                "lot_id": device.id,
                "product_id": device.product_id.id,
                "product_uom_id": device.product_id.uom_id.id,
                "location_id": self.current_quant(device).location_id.id,
                "scrap_location_id": scrap_loc.id,
                "date_expected": date,
            }
        )
        scrap.do_scrap()
        datet = datetime.combine(date, datetime.min.time())
        _set_date(scrap.move_id, datet, "date")
        quant = self.current_quant(device)
        _set_date(quant, datet, "in_date")
        return scrap

    def receive_device(self, serial, contract, date):
        lot_id = (
            self.env["stock.production.lot"]
            .search([("name", "=", serial)])
            .ensure_one()
        )
        loc = self.env.ref("commown_devices.stock_location_devices_to_check")
        contract.receive_device(lot_id, loc, date=date, do_transfer=True)
