from odoo import _, fields


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


def first_common_location(locs):
    """From a list of locations return the first common parent location.
    Retun a falsy stock.location if there is no common location.
    """
    env = locs[0].env
    if len(locs) == 1:
        return locs[0]
    else:
        loc1 = locs[0]
        loc2 = first_common_location(locs[1:])
        if loc1 and loc2:
            path_loc1 = loc1.parent_path[:-1].split("/")
            path_loc2 = loc2.parent_path[:-1].split("/")
            if set(path_loc1).intersection(set(path_loc2)):
                common_loc_id = int(
                    [a for a in path_loc1 if a in path_loc2 and a != ""][-1]
                )
                return env["stock.location"].browse(common_loc_id)
            else:
                return env["stock.location"]
        else:
            return env["stock.location"]


def find_products_orig_location(env, products, stock=None):
    """From a dictionary {product: quantity}
    find the location from where product
    can be sent"""
    if stock == None:
        stock = env.ref("stock.stock_location_stock")
    pts_orig = {}
    for product, quantity_to_send in products.items():
        quant = (
            env["stock.quant"]
            .search(
                [
                    ("product_id", "=", product.id),
                    ("location_id", "child_of", stock.id),
                ]
            )
            .filtered(
                lambda q, qts=quantity_to_send: q.quantity - q.reserved_quantity >= qts
            )
        )
        if not quant:
            raise Warning(_("Not enough %s in stock") % product.name)

        pts_orig[product] = {"qty": quantity_to_send, "loc": quant[0].location_id}

    return pts_orig


def internal_picking_mixt(
    lots,
    products,
    dest_location,
    origin,
    date=None,
    do_transfer=False,
):
    """Create picking with tracked and untracked products"""
    env = dest_location.env
    located_products = find_products_orig_location(env, products)
    products_locations = [located_products[p]["loc"] for p in located_products.keys()]

    located_lots = {
        lot: {
            "loc": lot.current_location(
                env.ref("commown_devices.stock_location_available_for_rent"),
                raise_if_not_found=True,
                raise_if_reserved=True,
            )
        }
        for lot in lots
    }

    lots_locations = [located_lots[l]["loc"] for l in located_lots.keys()]

    picking_type = env.ref("stock.picking_type_internal")

    date = date or fields.Datetime.now()

    picking_orig_location = first_common_location(products_locations + lots_locations)
    picking = env["stock.picking"].create(
        {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": picking_orig_location.id,
            "location_dest_id": dest_location.id,
            "date": date,
            "date_done": date,
            "origin": origin,
        }
    )

    moves_lots = {}
    for lot in located_lots.keys():
        moves_lots[lot] = env["stock.move"].create(
            {
                "name": lot.product_id.name,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
                "location_id": located_lots[lot]["loc"].id,
                "location_dest_id": dest_location.id,
                "product_id": lot.product_id.id,
                "product_uom_qty": lot.product_qty,
                "product_uom": lot.product_uom_id.id,
                "date": date,
            }
        )

    moves_products = {}
    for product, pt_info in located_products.items():
        moves_products[product] = env["stock.move"].create(
            {
                "name": product.name,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
                "location_id": pt_info["loc"].id,
                "location_dest_id": dest_location.id,
                "product_id": product.id,
                "product_uom_qty": pt_info["qty"],
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

    for lot, move in moves_lots.items():
        move.move_line_ids.update(
            {
                "lot_id": lot.id,
                "location_id": located_lots[lot]["loc"].id,
                "qty_done": lot.product_qty,
            }
        )

    for product, move in moves_products.items():
        move.move_line_ids.update(
            {
                "location_id": located_products[product]["loc"].id,
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
