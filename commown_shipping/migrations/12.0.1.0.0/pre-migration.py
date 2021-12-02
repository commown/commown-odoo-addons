# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

_column_renames = {
    "project_project": [
        ("shipping_account_id", None),
    ],
    "crm_team": [
        ("shipping_account_id", None),
    ]
}


@openupgrade.migrate()
def migrate(env, version):
    cr = env.cr
    openupgrade.rename_columns(cr, _column_renames)
