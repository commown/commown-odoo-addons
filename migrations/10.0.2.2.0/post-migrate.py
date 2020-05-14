from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    cr.execute(
        'UPDATE product_template'
        ' SET rental_price = list_price / ('
        '  CASE deposit_price_to_lease_amount_ratio'
        '    WHEN 0 THEN 1'
        '    ELSE deposit_price_to_lease_amount_ratio'
        '  END'
        ')'
        ' WHERE is_rental=TRUE'
        )
