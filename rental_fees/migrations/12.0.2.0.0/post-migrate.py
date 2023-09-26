def migrate(cr, version):
    # Set detail fees def from old computation fees def column
    cr.execute(
        "UPDATE rental_fees_computation_detail "
        "SET fees_definition_id = C.old_fees_definition_id "
        "FROM rental_fees_computation AS C "
        "WHERE C.id = fees_computation_id"
    )

    # Insert computation > definition relations in the Many2many table
    cr.execute(
        "INSERT INTO rental_fees_computation_rental_fees_definition_rel"
        " (rental_fees_computation_id, rental_fees_definition_id) "
        "SELECT id, old_fees_definition_id FROM rental_fees_computation"
    )

    # ... then drop the old column
    cr.execute(
        "ALTER TABLE rental_fees_computation " "DROP column old_fees_definition_id"
    )

    # Set fees def on invoice line from invoice computation_id column
    cr.execute(
        "WITH invl_to_def AS ("
        " SELECT INVL.id as invl_id, CD.rental_fees_definition_id as def_id"
        " FROM"
        "  rental_fees_computation_rental_fees_definition_rel AS CD,"
        "  account_invoice INV,"
        "  account_invoice_line INVL"
        " WHERE"
        "  INVL.invoice_id = INV.id"
        "  AND INV.fees_computation_id = CD.rental_fees_computation_id"
        ") "
        "UPDATE account_invoice_line "
        "SET fees_definition_id = invl_to_def.def_id "
        "FROM invl_to_def "
        "WHERE"
        " invl_to_def.invl_id = id"
        " AND fees_definition_id is NULL"
    )


# Check: number of invoice lines of computation invoices must equal the number of
# invoice lines of same computation's definitions
# clines = env["rental_fees.computation"].search([]).mapped("invoice_ids.invoice_line_ids")
# dlines = env["rental_fees.definition"].search([]).mapped("invoice_line_ids")
# assert clines == dlines
