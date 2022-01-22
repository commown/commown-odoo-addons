from datetime import datetime
import hashlib
import logging
import urllib
from pprint import pformat

import pytz
import iso8601
import phonenumbers
import requests

from odoo import _


_logger = logging.getLogger(__name__)
MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE


def coop_ws_base_url(env):
    return env['ir.config_parameter'].get_param(
        'commown_cooperative_campaign.base_url')


def phone_to_coop_id(salt, country_code, *phone_nums):

    if not country_code:
        return None

    for phone_num in phone_nums:
        if not phone_num:
            continue
        phone_obj = phonenumbers.parse(phone_num, country_code)
        if phonenumbers.number_type(phone_obj) == MOBILE_TYPE:
            phone = phonenumbers.format_number(
                phone_obj, phonenumbers.PhoneNumberFormat.NATIONAL
            ).replace(' ', '')
            return hashlib.sha256(phone + salt).hexdigest()

    return None


def parse_ws_date(str_date):
    "Return a timezone naive UTC date from given str_date"
    _date = iso8601.parse_date(str_date)
    return _date.replace(tzinfo=None) - _date.utcoffset()


def format_ws_date(str_date, dt_format):
    return parse_ws_date(str_date).strftime(dt_format)


def coop_ws_query(base_url, campaign_ref, customer_key):
    "Query the cooperative web services to see if a subscription is active"

    _logger.info(u"Querying %s, campaign %s, identifier %s",
                 base_url, campaign_ref, customer_key)

    url = (base_url + "/campaigns/%s/subscriptions/important-events"
           % urllib.quote_plus(campaign_ref))
    resp = requests.get(url, params={"customer_key": customer_key})
    resp.raise_for_status()

    subscriptions = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(subscriptions))
    return subscriptions


def coop_ws_valid_subscriptions(subscriptions, date, hour=12):
    if subscriptions:
        events = {e["type"]: parse_ws_date(e["ts"])
                  for e in subscriptions[0]["events"]}
        dt = datetime(date.year, date.month, date.day, hour=hour)
        if "optin" not in events or events["optin"] >= dt:
            return False
        if "optout" in events and events["optout"] < dt:
            return False
        return True


def _hr_details(subscription_details, dt_format):
    result = []
    for member, details in subscription_details.items():
        if "optin_ts" not in details:
            result.append(_("not subscribed"))
        else:
            optin = format_ws_date(details["optin_ts"], dt_format)
            optout = (u"..." if not details["optout_ts"]
                      else format_ws_date(details["optout_ts"], dt_format))
        result.append((u"- %s: %s" % (member, u"%s >> %s" % (optin, optout))))
    return u"\n".join(result)


def coop_human_readable_subscriptions(subscriptions, dt_format):
    if not subscriptions:
        return _("No subscription at all (by any partner)")

    result = "" if len(subscriptions) == 1 else _("%d subscriptions:\n")

    for num, subscription in enumerate(subscriptions):
        if num:
            result += u"\n\n"
        ctx = {
            "key": subscription["customer_key"],
            "validity": u" >> ".join(
                sorted(format_ws_date(e["ts"], dt_format)
                       for e in subscription["events"])),
            "details": _hr_details(subscription["details"], dt_format),
        }
        result += _("Validity: %(validity)s\n"
                    "--\n"
                    "Key: %(key)s\n"
                    "--\n"
                    "Subscription details:\n%(details)s\n"
                    ) % ctx
    return result


def coop_ws_optin(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to insert a new subscription"

    _logger.info(u"Optin %s: %s on %s...", campaign_ref, customer_key, date)

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optin_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-in" % urllib.quote_plus(campaign_ref)
    resp = requests.post(
        url, json={"customer_key": customer_key, "optin_ts": optin_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(resp_data))


def coop_ws_optout(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to cancel a subscription"

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optout_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-out" % urllib.quote_plus(campaign_ref)

    _logger.info(
        u"Setting optout on %s in coop campaign %s, identifier %s using %s...",
        optout_ts, campaign_ref, customer_key, url)

    resp = requests.post(
        url, json={"customer_key": customer_key, "optout_ts": optout_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(resp_data))
