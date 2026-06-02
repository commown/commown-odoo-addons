import datetime
from functools import partial

from odoo import _, fields, models
from odoo.exceptions import UserError


def _assigned(picking):
    return picking.state == "assigned"


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


def find_products_orig_location(
    env, products, stocks=None, compute_summary=False, _raise=True
):
    """From a dictionary {product: quantity} find the location from where product can be
    sent and produce a summary to tell user where each product should be sent from.
    `stocks` parameter is a list of stock.location to look in for `products` ordered by
    preference"""
    if stocks is None:
        stocks = env.ref("commown_devices.stock_location_available_for_rent")
    pts_orig = {}

    def enough_to_send(q, to_send):
        return q.quantity - q.reserved_quantity >= to_send

    def qsearch(product, stock):
        return env["stock.quant"].search(
            [("product_id", "=", product.id), ("location_id", "child_of", stock.id)]
        )

    for product, quantity_to_send in products.items():
        if getattr(product, "_origin", None):
            product = product._origin
        enough_in_quant = partial(enough_to_send, to_send=quantity_to_send)
        location = None
        for stock in stocks:
            quants = qsearch(product, stock).filtered(enough_in_quant)
            if quants:
                location = quants[0].location_id
                break
        else:
            if _raise:
                ctx = {
                    "product": product.name,
                    "locs": ", ".join(stocks.mapped("name")),
                }
                msg = _("Not enough %(product)s under location(s) %(locs)s") % ctx
                raise UserError(msg)

        pts_orig[product] = {"qty": quantity_to_send, "loc": location}
    if compute_summary:
        location_summary_dict = {}
        for pt, pt_infos in pts_orig.items():
            location_summary_dict.setdefault(pt_infos["loc"], []).append(pt)
        summary = []
        for loc in location_summary_dict.keys():
            ctx = {
                "loc": loc.name if loc else _("Not in stock"),
                "products": ", ".join(pt.name for pt in location_summary_dict[loc]),
            }
            summary.append(_("%(loc)s: %(products)s") % ctx)
            if loc is None:
                env.user.notify_info(summary[-1], sticky=True)
    else:
        summary = ["Summary hasn't been computed"]

    return {"pts_orig": pts_orig, "text_summary": "\n".join(summary)}


def create_move_from_lots(picking, located_lots):
    """Create a stock move for each lot. Do not reuse existing move because we might want to
    assign them to different contracts.
    The stock.move.line are automatically created when the picking is assigned"""
    env = picking.env
    moves_by_lot = {}
    for lot in located_lots:
        stock_move = env["stock.move"].create(
            {
                "name": lot.product_id.name,
                "picking_id": picking.id,
                "picking_type_id": picking.picking_type_id.id,
                "location_id": located_lots[lot]["loc"].id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": lot.product_id.id,
                "product_uom_qty": 1,
                "product_uom": lot.product_uom_id.id,
                "date": picking.date,
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
            }
        )
        moves_by_products[product] = stock_move
    return moves_by_products


def internal_picking(
    lots,  # recordset of stock.lot
    products,  # dict {product : quantity}
    send_nonserial_products_from,
    send_lots_from,
    dest_location,
    origin_document,
    date=None,
):
    """Create picking with tracked and untracked products, if a picking is passed as an
    argument, try to update the existing picking with new move lines"""

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

    lots_locations = [located_lots[lot]["loc"] for lot in located_lots.keys()]

    date = date or fields.Datetime.now()

    picking_type = env.ref("stock.picking_type_internal")

    picking_orig_location = first_common_location(products_locations + lots_locations)
    picking = env["stock.picking"].create(
        {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": picking_orig_location.id,
            "location_dest_id": dest_location.id,
            "date": date,
            "date_done": date,
            "origin_document_id": origin_document and origin_document.id,
            "origin_document_model": origin_document and origin_document._name,
        }
    )
    picking.scheduled_date = date

    moves_by_lots = create_move_from_lots(picking, located_lots)
    moves_by_products = search_or_create_move_from_products(picking, located_products)

    assert picking.move_ids
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
    for move in picking.move_ids:
        _set_date(move, date, "date")
    for move_line in picking.move_line_ids:
        _set_date(move_line, date, "date")
        for quant in move_line.lot_id.quant_ids:
            if quant.quantity > 0 and quant.location_id == loc:
                _set_date(quant, date, "in_date")


def _force_scrap_date(scrap, date):
    _set_date(scrap, date, "date_done")
    loc = scrap.scrap_location_id
    _set_date(scrap.move_id, date, "date")
    for move_line in scrap.move_id.move_line_ids:
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


class ToCustomerPickingMixin(models.AbstractModel):
    _name = "to.customer.picking.mixin"
    _description = (
        "Abstract class for obect that use wizard to send device to a customer"
    )

    delivery_time = datetime.time(9, 0)

    def action_to_customer_picking(self):
        contract = self.contract_id

        if contract.pending_picking():
            raise UserError(
                _(
                    "The contract has already assigned picking(s)!\n"
                    "Either cancel, scrap or validate it."
                )
            )

        res_model = self._name + ".to.customer.wizard"
        view = self.env["ir.ui.view"].search(
            [("model", "=", res_model), ("type", "=", "form")],
            limit=1,
        ) or self.env.ref("commown_devices.wizard_abstract_to_customer_form")

        return {
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "name": _("Send a device"),
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {"default_entity_id": self.id},
        }

    def delivery_perform_actions(self):
        "Validate shipping and start contract"
        res = super().delivery_perform_actions()

        picking = self.contract_id.move_ids.mapped("picking_id").filtered(_assigned)
        if len(picking) == 1:
            # time doesn't really matter for now; ideally
            # deliver_date would become delivery_datetime:
            do_new_transfer(
                picking,
                datetime.datetime.combine(self.delivery_date, self.delivery_time),
            )

        if self.contract_id:
            # Current method may be called by users not allowed to update
            # contracts, so we use sudo here:
            contract = self.contract_id.sudo()
            # Do not restart a contract that has already started
            if not contract.date_start or contract.date_start > datetime.date.today():
                contract.date_start = self.delivery_date
        return res
