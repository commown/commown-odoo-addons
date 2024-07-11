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

    cmodel = env["contract.contract"].with_context(no_raise_in_update_lot_contract=True)
    for contract in cmodel.search([]):
        contract.move_ids.sorted("date").update_lot_contract()
