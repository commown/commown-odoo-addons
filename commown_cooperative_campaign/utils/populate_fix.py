import phonenumbers


c_names = """SO07585-01
SO07635-01
SO06819-01
SO06826-01
SO06402-01
SO06347-01
SO06186-01
SO06107-01
SO05556-01
SO05006-01
SO05013-01
SO04694-01
SO04588-01
SO04449-01
SO04419-01
SO04392-01
SO04218-01
SO03996-01
SO03641-01
SO03537-01
SO03566-01
SO03465-01
SO03237-01
SO03182-01
SO02943-01
SO02818-01
SO02840-01
SO356-01
""".split()


def main(env, c_names, campaign_name=u"TeleCommown2021"):
    campaign = env["coupon.campaign"].search([('name', '=', campaign_name)])

    done = set()

    cs = env["account.analytic.account"].search([("name", "in", c_names)])
    assert len(cs) == len(c_names)

    for contract in cs:
        partner = contract.partner_id

        if partner in done:
            print "SKIP Contract %s (%s): already done" % (
                contract.name, partner.name)
            continue

        if partner.country_id.code != u"FR":
            print "SKIP Contract %s (%s): country is %s" % (
                contract.name, partner.name, partner.country_id.code)
            continue

        if partner.commercial_partner_id != partner:
            print "SKIP Contract %s (%s): B2B (%s)" % (
                contract.name, partner.name, partner.commercial_partner_id.name)
            continue

        so = contract.mapped(
            "recurring_invoice_line_ids.sale_order_line_id.order_id"
        )
        if len(so) != 1:
            print u"SKIP %s: %d sale(s) attached" % (contract.name, len(so))
            continue

        customer_key = None
        try:
            customer_key = campaign.coop_partner_identifier(partner)
        except phonenumbers.NumberParseException:
            print "INFO Contract %s (%s): error parsing phone number %s" % (
                contract.name, partner.name, (partner.mobile or partner.phone))

        if customer_key:
            print "INFO Contract %s (%s): has key %s" % (
                contract.name, partner.name, customer_key)

        coupon = so.reserve_coupon(campaign.name)
        coupon.update({'used_for_sale_id': so.id,
                       'reserved_for_sale_id': False})
        print "DONE Contract %s (%s): so %s has coupon %s" % (
            contract.name, partner.name, so.name, coupon.code)
        done.add(partner)
