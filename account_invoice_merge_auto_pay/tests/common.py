def inject_payment_data(cls, partner):
    electronic_in = cls.env["account.payment.method"].create(
        {
            "name": "Electronic In",
            "code": "electronic",
            "payment_type": "inbound",
        }
    )

    electronic_out = cls.env["account.payment.method"].create(
        {
            "name": "Electronic Out",
            "code": "electronic",
            "payment_type": "outbound",
        }
    )

    cls.customer_journal = cls.env["account.journal"].create(
        {
            "name": "Customer journal",
            "code": "RC",
            "company_id": cls.env.company.id,
            "type": "bank",
        }
    )

    payment_mode_out = cls.env["account.payment.mode"].create(
        {
            "name": "Electronic outbound to customer journal",
            "payment_method_id": electronic_out.id,
            "payment_type": "outbound",
            "bank_account_link": "fixed",
            "fixed_journal_id": cls.customer_journal.id,
        }
    )

    cls.payment_mode = cls.env["account.payment.mode"].create(
        {
            "name": "Electronic inbound to customer journal",
            "payment_method_id": electronic_in.id,
            "payment_type": "inbound",
            "bank_account_link": "fixed",
            "fixed_journal_id": cls.customer_journal.id,
            "refund_payment_mode_id": payment_mode_out.id,
        }
    )

    provider = cls.env.ref("payment.payment_provider_stripe")
    provider.sudo().state = "enabled"

    token = (
        cls.env["payment.token"]
        .sudo()
        .create(
            {
                "payment_details": "test payment token",
                "partner_id": partner.id,
                "provider_id": provider.id,
                "provider_ref": "test ref",
            }
        )
    )
    partner.update(
        {
            "customer_payment_mode_id": cls.payment_mode.id,
            "payment_token_id": token.id,
            "invoice_merge_next_date": "2019-05-15",
            "invoice_merge_recurring_rule_type": "monthly",
            "invoice_merge_recurring_interval": 1,
        }
    )
