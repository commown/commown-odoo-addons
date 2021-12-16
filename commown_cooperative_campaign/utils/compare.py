from odoo.addons.commown_cooperative_campaign.models.coupon import mobile_phone


def last_invoice(partner, campaign_name, contract=None):
    domain = [
        ("type", "=", "out_invoice"),
        ("journal_id.type", "=", "sale"),
        ("partner_id", "in", partner.ids),
    ]

    if campaign_name is not None:
        domain.append(("invoice_line_ids", "like", campaign_name))

    if contract is not None:
        domain.append(("contract_id", "in", contract.ids))

    return partner.env["account.invoice"].search(
        domain, limit=1, order="date_invoice DESC")


def get_campaign(env, campaign_name=u"TeleCommown2021"):
    return env["coupon.campaign"].search([
        ("name", "=", campaign_name),
        ("is_coop_campaign", "=", True),
    ]).ensure_one()


def export(env, campaign_name=u"TeleCommown2021"):

    campaign = get_campaign(env)

    partners = env["account.invoice"].search([
        ("type", "=", "out_invoice"),
        ("journal_id.type", "=", "sale"),
        ("invoice_line_ids", "like", campaign_name),
    ]).mapped("partner_id")

    for partner in partners:
        print ",".join([
            campaign.coop_partner_identifier(partner),
            partner.display_name,
            mobile_phone(partner, u"FR"),
            last_invoice(partner, campaign_name).date_invoice,
        ])


def has_coupon(contract, campaign_name=u"TeleCommown2021"):
    sale = contract.mapped(
        "recurring_invoice_line_ids.sale_order_line_id.order_id")
    return sale.used_coupons().filtered(
        lambda c: c.campaign_id.name == campaign_name)


def has_active_contract_with_coupon(partner, campaign_name=u"TeleCommown2021"):
    return partner.env["account.analytic.account"].search([
        ("recurring_invoices", "=", True),
        ("date_end", "=", False),
        ("partner_id", "in", partner.ids),
    ]).filtered(lambda c: has_coupon(c, campaign_name))


def from_phones(env, phone_nums, campaign_name=u"TeleCommown2021"):
    campaign = get_campaign(env)
    E164 = phonenumbers.PhoneNumberFormat.E164
    errors = []

    for phone_num in phone_nums:
        phone_obj = phonenumbers.parse(phone_num, "FR")
        phone_e164 = phonenumbers.format_number(phone_obj, E164)

        partner = env["res.partner"].search([
            ("parent_id", "=", False),
            '|',
            ("mobile", "=", phone_e164),
            ("phone", "=", phone_e164),
        ])

        if not partner:
            errors.append(u"ERROR: Cannot find phone num %s" % phone_e164)
            continue
        elif len(partner) > 1:
            errors.append("WARNING: %d partners with the same id! %s" % (
                len(partner), u", ".join(partner.mapped("name"))))

        contract = has_active_contract_with_coupon(partner, campaign_name)
        inv = last_invoice(partner, None, contract)
        assert inv.contract_id.id in contract.ids

        print ",".join([
            campaign.coop_partner_identifier(inv.partner_id),
            inv.partner_id.display_name,
            phone_e164,
            inv.date_invoice,
            str(any(campaign_name in l.name for l in inv.invoice_line_ids)),
            str(len(contract)),
        ])

        if errors:
            print u"Errors occurred:\n%s" % u"\n".join(errors)
