from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute(
            """
        UPDATE stock_move AS M
        SET contract_id=P._temp_contract_id
        FROM stock_picking AS P
        WHERE P.id=M.picking_id
        AND P._temp_contract_id is not NULL
        """
        )
        env.cr.execute(
            """
        ALTER TABLE stock_picking
        DROP COLUMN _temp_contract_id
        """
        )

    def sql_delete(objs):
        if not objs:
            return
        table = objs._name.replace(".", "_")
        cr = objs.env.cr
        cr.execute(
            "DELETE FROM %s WHERE id IN (%s)"
            % (table, ",".join(str(_id) for _id in objs.ids))
        )

    def remove_scrap(env, scrap):
        sql_delete(scrap.move_id.move_line_ids)
        sql_delete(scrap.move_id)
        sql_delete(scrap)

    # Clean scrap that were made to a device that was already in scrap location
    scrap_loc = env.ref("stock.stock_location_scrapped")
    scraps_from_scrap = env["stock.scrap"].search([("location_id", "=", scrap_loc.id)])
    for s in scraps_from_scrap:
        remove_scrap(env, s)

    # Remove origin on scrap that were made from "Casse" taks
    # it is normalment made on diag card
    env["stock.move"].browse(
        [5365, 10761, 4112, 16371, 1690, 11224, 10764, 8342, 6925, 17381, 8341, 9609]
    ).mapped("scrap_ids").update({"origin": False})

    for scrap in env["stock.scrap"].search([("origin", "=like", "Task-%")]):
        task_id = int(scrap.origin[5:])
        task = env["project.task"].browse(task_id).exists()
        if task and task.contract_id:
            task.contract_id.move_ids |= scrap.move_id

            scrap.contract_id = task.contract_id.id
            if scrap.move_id:
                scrap.move_id.contract_id = task.contract_id.id

    # Fix a reception with wrong type
    env["stock.picking"].browse([1860, 10085]).update({"picking_type_id": 1})

    # Fix wrong history order
    pick1 = env["stock.picking"].browse(1309)
    date1 = pick1.move_lines.date

    pick2 = env["stock.picking"].browse(1622)
    date2 = pick2.move_lines.date

    pick1.scheduled_date = date2
    pick2.scheduled_date = date1

    pick1.action_set_date_done_to_scheduled()
    pick2.action_set_date_done_to_scheduled()

    model = env["stock.production.lot"].with_context(
        no_raise_in_update_lot_contract=True
    )
    for lot in model.search([]):
        lines = (
            lot.env["stock.move.line"]
            .search(
                [
                    "&",
                    "&",
                    "|",
                    ("move_id.picking_id.picking_type_id", "not in", [1, 10]),
                    ("move_id.scrapped", "=", True),
                    ("lot_id", "=", lot.id),
                    ("state", "=", "done"),
                ]
            )
            .sorted(lambda l: l.move_id.date)
        )

        for line in lines:
            line.move_id.update_lot_contract()

    # Ignore following errors:
    # -Contrat 975, Factice contract (no location)
    # -Contract 1032, Luc Blondy scrap cancel.
    # -Contract 3612, Julie Agor Cae location not created
    # -Contract 2192, Railcoop corrected in prod
    # -Contract 1466, corrected in prod
    # -Contract 1566, wrong device (nv41) sent on Bi Pharma instead of n131
    # -Contract 3370/3371, "Transition Developpement durable" corrected in prod
    # -Contract 1124, a scrap move made on picking can be ignored
    # -Contract 3889, double scrap corrected in prod and test

    env["ir.ui.view"].search([("arch_db", "like", "quant_nb")]).unlink()
