def migrate(cr, version):
    """We prepend 'contract:' to date reference when it was commitment_end_date.

    When it was 'date_start', we leave it as is although the meaning changes (from
    contract to contract line date_start attribute), because we want to refer to the
    contract line start date: this is more robust to contract line addition while the
    contract is already active.
    """

    for table in ("contract_discount_line", "contract_template_discount_line"):
        for attr in ("start_reference", "end_reference"):
            cr.execute(
                f"UPDATE {table} SET {attr}='contract:commitment_end_date'"
                f" WHERE {attr}='commitment_end_date';"
            )
