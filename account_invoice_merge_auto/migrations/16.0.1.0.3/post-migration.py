from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute(
        """
        UPDATE account_move mv
        SET auto_merge = inv.auto_merge
        FROM account_invoice inv
        WHERE inv.id = mv.old_invoice_id
        """
    )
