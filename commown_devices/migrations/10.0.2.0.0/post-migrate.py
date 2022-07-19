from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute(
            """
        UPDATE product_template AS PT1
        SET storable_product_id=PP.product_tmpl_id
        FROM product_product AS PP
        WHERE PP.id=PT1.__temp_storable_product_id
        """
        )
        env.cr.execute(
            """
        ALTER TABLE product_template
        DROP COLUMN __temp_storable_product_id
        """
        )
