# coding: utf-8

from __future__ import print_function

import contextlib
import datetime

import phonenumbers
import requests

from odoo import fields

from odoo.addons.commown_cooperative_campaign.models import ws_utils


TC2021_ID = 36


def telecoop_phone(partner):

    MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE
    for phone_num in (partner.mobile, partner.phone):
        if not phone_num:
            continue
        phone_obj = phonenumbers.parse(phone_num, "FR")
        if phonenumbers.number_type(phone_obj) == MOBILE_TYPE:
            return phonenumbers.format_number(
                phone_obj, phonenumbers.PhoneNumberFormat.NATIONAL
            ).replace(' ', '')


def telecommown_base_url(env):
    return env['ir.config_parameter'].get_param(
        'commown_cooperative_campaign.base_url')


def replace_subscription(campaign, old_key, new_key, date=None,
                         tz='Europe/Paris', **kw):

    if date is None:
        date = datetime.date.today()

    base_url = ws_utils.coop_ws_base_url(campaign.env)
    ws_utils.coop_ws_optout(base_url, campaign.name, old_key, date, tz)
    ws_utils.coop_ws_optin(base_url, campaign.name, new_key, date, tz)


def change_phonenumber(campaign, old_phone, partner):
    env = campaign.env
    acc = env["keychain.account"].search([
        ("technical_name", "=", campaign.name + "-salt"),
    ]).ensure_one()
    old_key = ws_utils.phone_to_coop_id(
        acc._get_password(), partner.country_id.code,
        partner.mobile, partner.phone)
    new_key = campaign.coop_partner_identifier(partner)
    if not new_key:
        raise ValueError(u"Cannot build new identifier for %s" % partner.name)
    replace_subscription(campaign, old_key, new_key, tz=partner.tz)


@contextlib.contextmanager
def json_exc(_raise=False):
    try:
        yield
    except requests.HTTPError as exc:
        print(exc)
        resp = exc.response
        if resp.status_code == 422:
            print("  > ", resp.json())
        if _raise:
            raise exc


def has_coupon(contract):
    sales = contract.mapped(
        "recurring_invoice_line_ids.sale_order_line_id.order_id")
    return contract.env["coupon.coupon"].search([
        ("used_for_sale_id", "in", sales.ids),
        ("campaign_id.name", "=", "TeleCommown2021")
    ])


def reactivate_subscribed_partners(env, debug=True):

    tc2021 = env["coupon.campaign"].browse(TC2021_ID)
    base_url = telecommown_base_url(env)
    optin_date = datetime.date(2022, 1, 1)

    inv_lines = env["account.invoice.line"].search([
        ("name", "like", tc2021.name),
    ])
    partners = inv_lines.mapped("invoice_id.partner_id")
    assert set(inv_lines.mapped("invoice_id.contract_id.date_end")) == {False}

    for partner in partners:
        key = tc2021.coop_partner_identifier(partner)
        with json_exc(False):
            print(u"opt-in partner %d: %s" % (partner.id, partner.name))
            if not debug:
                ws_utils.coop_ws_optin(base_url, tc2021.name, key, optin_date,
                                       partner.tz, hour=0)


def activate_asking_partners(env, debug=True):
    """1. vérifier droit à la réduction : contract actif avec coupon

    2. dans ce cas il a sûrement déjà une souscription TeleCommown2021 en BDD

       En fait non car :
       - certains clients sont arrivés entre la date de démarrage de la campagne
         (13/10/2021) et aujourd'hui
       - certains étaient bien arrivés avant mais n'avaient pas d'identifiant
       - certains sont des nouveaux qui ont oublié de saisir le code...

       Tactique :

       - on les efface tous et on opt-in les demandes valides

         delete from subscriptions
         where member_id=2
           and campaign_id=2
           and optin_ts < '2021-10-13 09:00:00+00';

       - on rattrape la facture oubliée grâce à une réduction ajoutée
         aux contrats en question

       - il faudra une procédure pour saisir l'opt-in des anciens qui
         le demandent : pas besoin on modifie la procédure de facturation
         pour inclure un optin systématique et alors pour souscrire quelqu'un
         de force il suffit de saisir un coupon dans un de ses contrats.


    3. si tout OK on met à jour la date de souscription à aujourd'hui ou on
       essaye optout

    """

    TC_STAGE_ID = 323

    leads = env["crm.lead"].search([("stage_id", "=", TC_STAGE_ID)])
    tc2021 = env["coupon.campaign"].browse(TC2021_ID)

    base_url = telecommown_base_url(env)
    min_optin_date = datetime.date(2022, 1, 1)

    def create_discount(cline):
        next_inv_date = fields.Date.from_string(
            cline.analytic_account_id.recurring_next_date)
        start_date = next_inv_date - datetime.timedelta(days=1)
        end_date = next_inv_date + datetime.timedelta(days=1)
        discount = env['contract.discount.line'].create({
            "name": u"TeleCommown2021 non prise en compte le mois dernier",
            "amount_type": u"fix",
            "amount_value": 1.5,
            "start_type": u"absolute",
            "start_date": fields.Date.to_string(start_date),
            "end_type": u"absolute",
            "end_date": fields.Date.to_string(end_date),
        })
        cline.specific_discount_line_ids |= discount
        return discount

    def ct_name(c):
        return u"%s (%s)" % (
            c.contract_template_id.name.split(u"/", 1)[0][:2],
            c.name)

    for lead in leads:
        partner = lead.partner_id
        print()

        # Must have a key
        key = tc2021.coop_partner_identifier(partner)
        assert key, "No key for %s" % partner.name

        # Must have an active contract with the expected coupon
        _contracts = env["account.analytic.account"].search([
            ("partner_id", "=", partner.id),
            ("recurring_invoices", "=", True),
            ("date_end", "=", False),
        ])
        contracts = _contracts.filtered(has_coupon)

        if not contracts:
            print(u"WARNING %s has no coupon" % partner.name)
            continue

        contract = contracts[0]

        # We do not like GS contracts as a support for TC
        if debug == "GS" and ct_name(contract)[:2] == "GS":
            print(len(_contracts),
                  ct_name(contract),
                  u"/",
                  u" - ".join(
                      ct_name(c) for c in _contracts if c != contract),
                  partner.name)

        optin_date = max(fields.Date.from_string(lead.create_date),
                         fields.Date.from_string(contract.date_start),
                         min_optin_date)

        with json_exc(False):  # XXX Turn into True in production?
            print(u";".join(["optin %s" % contract.name,
                             partner.name,
                             telecoop_phone(partner),
                             optin_date.isoformat()]))
            if not debug:
                ws_utils.coop_ws_optin(base_url, tc2021.name, key, optin_date,
                                       partner.tz, hour=0)

        last_invoice = env["account.invoice"].search([
            ("contract_id", "=", contract.id),
        ], order="date_invoice DESC", limit=1)
        if (fields.Date.from_string(last_invoice.date_invoice) >= optin_date
            and not any(
                tc2021.name in line.name
                for line in last_invoice.invoice_line_ids)):
            cline = contract.recurring_invoice_line_ids[0]
            print(u"Contract %s did not benefit from %s. Modifying line %s"
                  % (contract.name, tc2021.name, cline.name))
            if not debug:
                create_discount(cline)
            else:
                print("DEBUG mode: 2x discount for %s" % contract.name)
        else:
            print(u"!!! %s already benefits from %s"
                  % (contract.name, tc2021.name))

    return leads
