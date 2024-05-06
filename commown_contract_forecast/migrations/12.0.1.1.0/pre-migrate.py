def migrate(cr, version):
    "Add the computed field's column price_subtotal_taxed in an efficient way"

    cr.execute(
        "ALTER TABLE contract_line_forecast_period"
        " ADD COLUMN price_subtotal_taxed numeric;"
    )

    cr.execute(
        "UPDATE contract_line_forecast_period"
        " SET price_subtotal_taxed = 1.2 * price_subtotal;"
    )
