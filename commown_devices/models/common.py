from odoo import fields


def internal_picking_tracking_none(
    origin, products, orig_location, dest_location, date=None, do_transfer=False
):
    env = orig_location.env
    picking_type = env.ref("stock.picking_type_internal")

    date = date or fields.Datetime.now()

    picking = env["stock.picking"].create(
        {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "date": date,
            "date_done": date,
            "origin": origin,
        }
    )

    moves = {}
    for product, quantity in products.items():
        moves[product] = env["stock.move"].create(
            {
                "name": product.name,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
                "location_id": orig_location.id,
                "location_dest_id": dest_location.id,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "date": date,
            }
        )

    picking.scheduled_date = date

    assert picking.move_lines
    picking.action_confirm()
    picking.action_assign()
    assert picking.state == "assigned", (
        "Cannot assign any device: state keeps: %r" % picking.state
    )

    for product, move in moves.items():
        move.move_line_ids.update(
            {
                "location_id": orig_location.id,
                "qty_done": products[product],
            }
        )

    if do_transfer:
        do_new_transfer(picking, date)

    return picking


def internal_picking(
    origin, lots, orig_location, dest_location, date=None, do_transfer=False
):
    env = orig_location.env
    picking_type = env.ref("stock.picking_type_internal")

    date = date or fields.Datetime.now()

    picking = env["stock.picking"].create(
        {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "date": date,
            "date_done": date,
            "origin": origin,
        }
    )

    moves = {}
    for lot in lots:
        moves[lot] = env["stock.move"].create(
            {
                "name": lot.product_id.name,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
                "location_id": orig_location.id,
                "location_dest_id": dest_location.id,
                "product_id": lot.product_id.id,
                "product_uom_qty": lot.product_qty,
                "product_uom": lot.product_uom_id.id,
                "date": date,
            }
        )

    picking.scheduled_date = date

    assert picking.move_lines
    picking.action_confirm()
    picking.action_assign()
    assert picking.state == "assigned", (
        "Cannot assign any device: state keeps: %r" % picking.state
    )

    for lot, move in moves.items():
        move.move_line_ids.update(
            {
                "lot_id": lot.id,
                "location_id": orig_location.id,
                "qty_done": lot.product_qty,
            }
        )

    if do_transfer:
        do_new_transfer(picking, date)

    return picking


def do_new_transfer(picking, date):
    picking.button_validate()
    _force_picking_date(picking, date)


def _force_picking_date(picking, date):
    _set_date(picking, date, "date_done")
    loc = picking.location_dest_id
    for move in picking.move_lines:
        _set_date(move, date, "date")
    for move_line in picking.move_line_ids:
        _set_date(move_line, date, "date")
        for quant in move_line.lot_id.quant_ids:
            if quant.quantity > 0 and quant.location_id == loc:
                _set_date(quant, date, "in_date")


def _set_date(entity, value, attr_name):
    setattr(entity.sudo(), attr_name, value)
    sql = "UPDATE %s SET %s=%%s WHERE id=%%s" % (
        entity._name.replace(".", "_"),
        attr_name,
    )
    entity.env.cr.execute(sql, (str(value), entity.id))
