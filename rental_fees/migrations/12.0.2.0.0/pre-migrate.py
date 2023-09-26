def migrate(cr, version):
    cr.execute(
        "ALTER TABLE rental_fees_computation "
        "RENAME column fees_definition_id TO old_fees_definition_id"
    )
