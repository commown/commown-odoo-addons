def migrate(cr, version):
    cr.execute(
        """
    ALTER TABLE stock_picking
    RENAME COLUMN contract_id
    TO _temp_contract_id
    """
    )
