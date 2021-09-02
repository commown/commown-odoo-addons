from odoo import fields


def internal_picking(origin, lots, orig_location, dest_location,
                     date=None, do_transfer=False):
    env = orig_location.env
    picking_type = env.ref("stock.picking_type_internal")

    date = date or fields.Datetime.now()

    move_lines = []
    picking_data = {
        "move_type": "direct",
        "picking_type_id": picking_type.id,
        "location_id": orig_location.id,
        "location_dest_id": dest_location.id,
        "min_date": date,
        "date_done": date,
        "origin": origin,
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

    picking = env["stock.picking"].create(picking_data)
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
        do_new_transfer(picking, date)

    return picking


def do_new_transfer(picking, date):
    picking.do_new_transfer()
    _force_picking_date(picking, date)


def _force_picking_date(picking, date):
    _set_date(picking, date, 'date_done')
    for move in picking.move_lines:
        _set_date(move, date, 'date')
        for quant in move.quant_ids:
            _set_date(quant, date, 'in_date')


def _set_date(entity, value, attr_name):
    setattr(entity.sudo(), attr_name, value)
    sql = 'UPDATE %s SET %s=%%s WHERE id=%%s' % (
        entity._name.replace('.', '_'), attr_name)
    entity.env.cr.execute(sql, (str(value), entity.id))
