# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade
from psycopg2.extensions import AsIs


@openupgrade.migrate()
def migrate(env, version):

    mapping = {
        "colissimo-std-account": "shipping-account-colissimo-std-account",
        "colissimo-support-account": "shipping-account-colissimo-support-account",
    }

    for old_name, new_name in mapping.items():
        old_id = env["ir.model.data"].search([
            ('module', '=', 'commown_shipping'),
            ('name', '=', old_name)
        ]).res_id
        new_id = env["ir.model.data"].search([
            ('module', '=', 'commown_shipping'),
            ('name', '=', new_name)
        ]).res_id

        for table in ["project_project", "crm_team"]:
            openupgrade.logged_query(
                env.cr,
                """
                UPDATE %s
                SET shipping_account_id = %s
                WHERE %s = %s""", (
                    AsIs(table),
                    new_id,
                    AsIs(openupgrade.get_legacy_name('shipping_account_id')),
                    old_id
                ))
