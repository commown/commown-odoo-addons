from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute(
        """
        UPDATE project_task
        SET invoice_id = M.id
        FROM account_move M
        WHERE %s = M.old_invoice_id
        """
        % openupgrade.get_legacy_name("invoice_id")
    )
