def migrate(cr, version):
    cr.execute(
        """
    ALTER TABLE product_template
    RENAME COLUMN storable_product_id
    TO __temp_storable_product_id
    """
    )
