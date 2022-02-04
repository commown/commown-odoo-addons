# Copyright 2022 Sylvain LE GAL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade
from psycopg2 import sql

_logger = logging.getLogger(__name__)

def create_contract_records(cr):
    # Ref see :
    # OCA/contract/contract/migrations/12.0.4.0.0/pre-migration.py
    openupgrade.logged_query(
        cr, sql.SQL("""
        UPDATE account_analytic_account
        SET partner_id = 1
        WHERE id in (select distinct(contract_id) from project_task)
        AND id not in (select id from contract_contract)
        """),
    )

    openupgrade.logged_query(
        cr, sql.SQL("""
        INSERT INTO contract_contract
        SELECT * FROM account_analytic_account
        WHERE id in (select distinct(contract_id) from project_task)
        AND id not in (select id from contract_contract)
        """),
    )
    # Handle id sequence
    cr.execute("SELECT setval('contract_contract_id_seq', "
               "(SELECT MAX(id) FROM contract_contract))")
    cr.execute("ALTER TABLE contract_contract ALTER id "
               "SET DEFAULT NEXTVAL('contract_contract_id_seq')")


@openupgrade.migrate()
def migrate(env, version):
    cr = env.cr
    create_contract_records(cr)
