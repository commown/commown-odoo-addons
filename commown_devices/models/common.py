from functools import partial

from odoo import _, fields
from odoo.exceptions import UserError


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


def find_products_orig_location(env, products, stocks=None, compute_summary=False):
    """From a dictionary {product: quantity} find the location from where product can be
    sent and produce a summary to tell user where each product should be sent from.
    `stocks` parameter is a list of stock.location to look in for `products` ordered by
    preference"""
    if stocks is None:
        stocks = self.env.ref("commown_devices.stock_location_available_for_rent")
    pts_orig = {}
    enough_to_send = lambda q, to_send: q.quantity - q.reserved_quantity >= to_send
    for product, quantity_to_send in products.items():
        enough_in_quant = partial(enough_to_send, to_send=quantity_to_send)
        quants = env["stock.quant"]
        for stock in stocks:
            quants += (
                env["stock.quant"]
                .search(
                    [
                        ("product_id", "=", product.id),
                        ("location_id", "child_of", stock.id),
                    ]
                )
                .filtered(enough_in_quant)
            )
            if quants:
                break
        else:
            raise UserError(
                _("Not enough %s under location(s) %s")
                % (
                    product.name,
                    ", ".join(stocks.mapped("name")),
                )
            )

        pts_orig[product] = {"qty": quantity_to_send, "loc": quants[0].location_id}
    if compute_summary:
        location_summary_dict = {}
        for pt, pt_infos in pts_orig.items():
            location_summary_dict.setdefault(pt_infos["loc"], []).append(pt)
        location_summary = ""
        for loc in location_summary_dict.keys():
            location_summary += (
                loc.name
                + ": "
                + ", ".join(pt.name for pt in location_summary_dict[loc])
                + "\n"
            )
    else:
        location_summary = "Summary hasn't been computed"

    return {"pts_orig": pts_orig, "text_summary": location_summary}


def create_move_from_lots(picking, located_lots):
    """Create a stock move each lot. Do not réuse existing move because we might want to
    assign them to different contracts.
    The stock.move.line are automatically created when the picking is assigned"""
    env = picking.env
    moves_by_lot = {}
    for lot in located_lots.keys():
        stock_move = env["stock.move"].create(
            {
                "name": lot.product_id.name,
                "picking_id": picking.id,
                "picking_type_id": picking.picking_type_id.id,
                "location_id": located_lots[lot]["loc"].id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": lot.product_id.id,
                "product_uom_qty": lot.product_qty,
                "product_uom": lot.product_uom_id.id,
                "date": picking.date,
                "date_expected": picking.date,
            }
        )
        moves_by_lot[lot] = stock_move
    return moves_by_lot


def search_or_create_move_from_products(picking, located_products):
    """Create a move for each product of located_products."""
    env = picking.env
    moves_by_products = {}
    for product, pt_info in located_products.items():
        stock_move = env["stock.move"].create(
            {
                "name": product.name,
                "picking_id": picking.id,
                "picking_type_id": picking.picking_type_id.id,
                "location_id": pt_info["loc"].id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": product.id,
                "product_uom_qty": pt_info["qty"],
                "product_uom": product.uom_id.id,
                "date": picking.date,
                "date_expected": picking.date,
            }
        )
        moves_by_products[product] = stock_move
    return moves_by_products


def update_picking_datas(picking, from_locations, dest_location, origin):
    if picking.state in ("done", "cancel"):
        raise UserError(_("Can't reuse a picking in %r state") % picking.state)
    if picking.location_dest_id != dest_location:
        raise UserError(
            _(
                "Destination location of the picking to modify differs from the destination passed in argument"
            )
        )
    new_loc = first_common_location([picking.location_id] + from_locations)
    if not new_loc:
        raise UserError(
            _(
                "No commown location found between picking location and products/lots locations"
            )
        )

    picking.location_id = new_loc.id
    picking.origin += ", " + origin


def internal_picking(
    lots,  # list of lot
    products,  # dict {product : quantity}
    send_nonserial_products_from,
    send_lots_from,
    dest_location,
    origin,
    date=None,
    picking=None,
):
    """Create picking with tracked and untracked products, if a picking is passed as an
    argument it wil try to update the existing picking with new move_lines"""

    env = dest_location.env
    located_products = find_products_orig_location(
        env, products, send_nonserial_products_from
    )["pts_orig"]
    products_locations = [located_products[p]["loc"] for p in located_products.keys()]

    located_lots = {
        lot: {
            "loc": lot.current_location(
                send_lots_from,
                raise_if_not_found=True,
                raise_if_reserved=True,
            )
        }
        for lot in lots
    }

    lots_locations = [located_lots[l]["loc"] for l in located_lots.keys()]

    date = date or fields.Datetime.now()

    if picking is not None:
        update_picking_datas(
            picking, products_locations + lots_locations, dest_location, origin
        )

    else:
        picking_type = env.ref("stock.picking_type_internal")

        picking_orig_location = first_common_location(
            products_locations + lots_locations
        )
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
    picking.scheduled_date = date

    moves_by_lots = create_move_from_lots(picking, located_lots)
    moves_by_products = search_or_create_move_from_products(picking, located_products)

    assert picking.move_lines
    picking.with_context(dont_merge_moves=True).action_confirm()
    picking.action_assign()
    assert picking.state == "assigned", (
        "Cannot assign any device: state keeps: %r" % picking.state
    )

    new_moves = env["stock.move"]

    for lot, move in moves_by_lots.items():
        line = move.move_line_ids
        line.ensure_one()
        line.update(
            {"lot_id": lot.id, "qty_done": 1.0, "location_id": located_lots[lot]["loc"]}
        )
        new_moves |= move

    for product, move in moves_by_products.items():
        line = move.move_line_ids
        line.ensure_one()
        line.update({"qty_done": located_products[product]["qty"]})
        new_moves |= move

    return new_moves


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
