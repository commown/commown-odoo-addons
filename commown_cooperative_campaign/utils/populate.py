import urllib.parse

import requests

from odoo.fields import Date

from odoo.addons.commown_cooperative_campaign.models.discount import (
    coop_ws_optin)


class ContractError(Exception):
    pass


def handle_by_name(env, contract_name, campaign_name):
    base_url = env['ir.config_parameter'].sudo().get_param(
        'commown_cooperative_campaign.base_url')
    contract = env["contract.contract"].search(
        [("name", "=", "SO07491-01")]).ensure_one()
    campaign = env["coupon.campaign"].search(
        [("name", "=", campaign_name)]).ensure_one()
    handle_contract(base_url, contract, campaign)
    return contract, campaign


def handle_contract(base_url, contract, campaign, seen_keys=set()):

    if contract.partner_id.commercial_partner_id != contract.partner_id:
        raise ContractError("B2B - %s" % contract.name)

    customer_key = campaign.coop_partner_identifier(contract.partner_id)
    if not customer_key:
        raise ContractError("NOID - %s: %s" % (
            contract.name, contract.partner_id.name))
    if customer_key in seen_keys:
        raise ContractError("SK - %s key already seen" % contract.name)

    # Create a coupon
    so = contract.mapped(
        "recurring_invoice_line_ids.sale_order_line_id.order_id"
    )

    if len(so) != 1:
        raise ContractError("ERR - %s: %d sale(s) attached" % (
            contract.name, len(so)))

    if campaign in so.reserved_coupons().mapped("campaign_id"):
        seen_keys.add(customer_key)
        raise ContractError("DONE - %s has already a coupon" % contract.name)

    coupon = so.reserve_coupon(campaign.name)
    if not coupon:
        raise ContractError("NOCOUPON - %s : could not reserve a coupon"
                            % contract.name)
    coupon.update({'used_for_sale_id': so.id, 'reserved_for_sale_id': False})

    print(
        (" ".join([campaign.name, contract.name,
                   contract.date_start, customer_key])
         ).encode("utf-8")
    )

    coop_ws_optin(base_url,
                  campaign.name,
                  customer_key,
                  Date.from_string(contract.date_start),
                  contract.partner_id.tz)

    seen_keys.add(customer_key)


def new_campaign(env, base_url, campaign_name):

    orig_kc = env.ref("commown_cooperative_campaign.telecommown2021-salt")
    orig_kc.copy({
        "name": "Salt of %s" % campaign_name,
        "technical_name": campaign_name + "-salt",
        "clear_password": orig_kc._get_password(),
    })

    campaign = env["coupon.campaign"].create({
        "name": campaign_name,
        "is_coop_campaign": True,
        "is_without_coupons": True,
        "can_cumulate": True,
        "seller_id": 1,
    })

    resp = requests.post(base_url + "/campaigns/", json={
        "ref": campaign_name,
        "start_ts": "2021-10-18T09:00:00.00+02:00",
        "end_ts": "2022-12-31T23:59:59.00+01:00",
        "member_ids": [1, 2]
    })
    resp.raise_for_status()

    return campaign


def main(env, campaign_name, base_url=None, create_campaign=False,
         add_contract_reduction=False, register_contracts=False):

    if base_url is None:
        base_url = env['ir.config_parameter'].sudo().get_param(
            'commown_cooperative_campaign.base_url')

    if create_campaign:
        campaign = new_campaign(env, base_url, campaign_name)
    else:
        campaign = env["coupon.campaign"].search([
            ("name", "=", campaign_name),
            ("is_coop_campaign", "=", True),
            ("is_without_coupons", "=", True),
        ]).ensure_one()

    contract_templates = env["contract.template"].search([
        ("name", "like", "/B2C/"),
    ])

    if add_contract_reduction:
        ctdl_model = env["contract.template.discount.line"]
        for ct in contract_templates:
            for ctl in ct.recurring_invoice_line_ids:
                if "#START#" in ctl.name:  # no ##PRODUCT## in old contracts
                    if campaign not in ctl.mapped(
                            "discount_line_ids.coupon_campaign_id"):
                        ctl.discount_line_ids |= ctdl_model.create({
                            "contract_template_line_id": ctl.id,
                            "coupon_campaign_id": campaign.id,
                            "name": campaign_name,
                            "condition": "coupon_from_campaign",
                            "amount_type": "fix",
                            "amount_value": 1.5,
                            "start_type": "absolute",
                            "start_date": "2021-10-18",
                            "end_type": "absolute",
                            "end_date": "2022-12-31",
                        })
                    break
            else:
                raise ValueError(
                    "Could not add reduction to contract model %s" % ct.name)
            env.cr.commit()

    if register_contracts:
        contracts = env["contract.contract"].search([
            ("recurring_invoices", "=", True),
            ("date_end", "=", False),
            ("date_start", "<", "TODAY"),
            ("partner_id.country_id.code", "=", "FR"),
            ("contract_template_id", "in", contract_templates.ids),
        ], order="date_start DESC")

        seen_keys = set()

        for contract in contracts:

            try:
                with env.cr.savepoint():
                    handle_contract(base_url, contract, campaign, seen_keys)
            except ContractError as exc:
                print(("*** %s" % exc).encode("utf-8"))
                continue
            except requests.HTTPError as exc:
                print(contract.name.encode("utf-8") + " - " + str(exc))
                continue
            else:
                env.cr.commit()

    return campaign


def check_for_full_registered(env, campaign_name):
    campaign = env["coupon.campaign"].search([('name', '=', campaign_name)])
    base_url = (
        env['ir.config_parameter'].get_param(
            'commown_cooperative_campaign.base_url')
        + '/campaigns/%s/subscriptions/important-events' % (
            urllib.parse.quote_plus(campaign_name))
    )

    sos = campaign.coupon_ids.mapped(
        "used_for_sale_id").filtered(lambda so: so.state == "sale")

    for index, so in enumerate(sos):
        if not index % 10:
            print("%d / %d" % (index, len(sos)))
        partner = so.partner_id
        customer_key = campaign.coop_partner_identifier(partner)
        url = base_url + ("?customer_key=%s"
                          % urllib.parse.quote_plus(customer_key))
        resp = requests.get(url)
        resp.raise_for_status()
        if resp.json():
            print("Double! %s / %s: %s" % (so.name, partner.name, url))
