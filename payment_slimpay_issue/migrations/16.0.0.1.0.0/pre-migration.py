from openupgradelib import openupgrade

_column_rename = {
    "project_task": [
        ("invoice_id", None),
    ],
}


@openupgrade.migrate()
def migrate(env, version):
    # Use account_move old_invoice_id column to find the target invoice

    env.cr.execute(
        "ALTER TABLE project_task DROP CONSTRAINT project_task_invoice_id_fkey"
    )
    openupgrade.rename_columns(env.cr, _column_rename)
