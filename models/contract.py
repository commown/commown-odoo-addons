import logging

from collections import OrderedDict

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


def _set_date(entity, value, attr_name):
    setattr(entity, attr_name, value)
    sql = 'UPDATE %s SET %s=%%s WHERE id=%%s' % (
        entity._name.replace('.', '_'), attr_name)
    entity.env.cr.execute(sql, (str(value), entity.id))


class Contract(models.Model):
    _inherit = "account.analytic.account"

    picking_ids = fields.One2many(
        "stock.picking",
        "contract_id",
        string=u"Pickings")

    quant_ids = fields.One2many(
        "stock.quant",
        string=u"Contract-related stock",
        compute="_compute_quant_and_lot_ids",
        store=False,
        readonly=True,
    )

    lot_ids = fields.One2many(
        "stock.production.lot",
        string=u"Contract-related devices",
        compute="_compute_quant_and_lot_ids",
        store=False,
        readonly=True,
    )

    @api.depends("picking_ids")
    def _compute_quant_and_lot_ids(self):
        for record in self:
            customer_loc = record.partner_id.property_stock_customer
            record.quant_ids = self.env["stock.quant"].search([
                ("history_ids.picking_id.contract_id", "=", record.id),
                ("location_id", "=", customer_loc.id)
            ], order="location_id desc")
            record.lot_ids = record.stock_at_date()

    def send_all_picking(self):
        self.ensure_one()

        ref = self.env.ref
        picking_type = ref("stock.picking_type_internal")
        orig_location = ref("commown_devices.stock_location_available_for_rent")

        dest_location = self.partner_id.set_customer_location()

        move_lines = []
        picking_data = {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "origin": self.name,
            "move_lines": move_lines,
        }

        for so_line in self.mapped(
                "recurring_invoice_line_ids.sale_order_line_id"):
            product = so_line.product_id.product_tmpl_id.stockable_product_id
            if product and product.tracking == "serial":
                move_lines.append((0, 0, {
                    "name": product.name,
                    "picking_type_id": picking_type.id,
                    "location_id": orig_location.id,
                    "location_dest_id": dest_location.id,
                    "product_id": product.id,
                    "product_uom_qty": so_line.product_uom_qty,
                    "product_uom": so_line.product_uom.id,
                }))

        if not move_lines:
            raise ValueError("No storable product found on contract %s"
                             % self.name)

        picking = self.env["stock.picking"].create(picking_data)
        picking.action_confirm()
        picking.action_assign()
        self.picking_ids |= picking

        return picking

    @api.multi
    def send_device(self, lot, orig_location, date=None, do_transfer=False):
        """ Create a picking from `orig_location` to partner's location.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        dest_location = self.partner_id.set_customer_location()
        return self._create_picking([lot], orig_location, dest_location,
                                    date=date, do_transfer=do_transfer)

    @api.multi
    def receive_device(self, lot, dest_location, date=False, do_transfer=False):
        """ Create a picking from partner's location to `dest_location`.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """

        orig_location = self.partner_id.set_customer_location()
        return self._create_picking([lot], orig_location, dest_location,
                                    date=date, do_transfer=do_transfer)

    def _create_picking(self, lots, orig_location, dest_location,
                        date=None, do_transfer=False):
        self.ensure_one()
        picking_type = self.env.ref("stock.picking_type_internal")

        date = date or fields.Datetime.now()

        move_lines = []
        picking_data = {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "min_date": date,
            "date_done": date,
            "origin": self.name,
            "move_lines": move_lines,
        }

        for lot in lots:
            move_lines.append((0, 0, {
                "name": lot.product_id.name,
                "picking_type_id": picking_type.id,
                "location_id": orig_location.id,
                "location_dest_id": dest_location.id,
                "product_id": lot.product_id.id,
                "product_uom_qty": lot.product_qty,
                "product_uom": lot.product_uom_id.id,
                "date": date,
            }))

        picking = self.env["stock.picking"].create(picking_data)
        picking.action_confirm()
        picking.action_assign()
        assert picking.state == u"assigned", "Cannot assign any device"

        pack_op = picking.pack_operation_product_ids.ensure_one()
        pack_op.pack_lot_ids.unlink()
        pack_op.write({'pack_lot_ids': [
            (0, 0, {'lot_id': lot.id,
                    'lot_name': lot.name,
                    'qty': lot.product_qty}
             ) for lot in lots
        ]})
        pack_op.save()

        if do_transfer:
            picking.do_new_transfer()
            for move in picking.move_lines:
                _set_date(move, date, 'date')
                for quant in move.quant_ids:
                    _set_date(quant, date, 'in_date')

        self.picking_ids |= picking
        return picking

    @api.multi
    def stock_at_date(self, date=None):
        "Return the lots at partner's location at the given date"
        self.ensure_one()

        if date is None:
            date = fields.Datetime.now()

        moves = self.env["stock.move"].search([
            ("picking_id.contract_id", "=", self.id),
            ("date", "<=", date),
        ], order="date ASC")

        lot_ids = OrderedDict()
        partner_loc = self.partner_id.set_customer_location()
        for m in moves:
            for l in m.mapped("lot_ids"):
                lot_ids.setdefault(l.id, 0)
                lot_ids[l.id] += m.location_dest_id == partner_loc and 1 or -1

        return self.env["stock.production.lot"].browse([
            l_id for (l_id, total) in lot_ids.items() if total > 0
        ])
