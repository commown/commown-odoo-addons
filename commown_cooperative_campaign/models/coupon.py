import datetime
import logging
import hashlib
import urllib

from pprint import pformat

import iso8601
import phonenumbers
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError


MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE


_logger = logging.getLogger(__file__)


def coop_ws_important_events(base_url, campaign_ref, customer_key):
    "Query the cooperative web services to see if a subscription is active"

    _logger.info(
        u"Querying %s, campaign %s, identifier %s", base_url, campaign_ref, customer_key
    )

    url = (
        base_url
        + "/campaigns/%s/subscriptions/important-events"
        % urllib.parse.quote_plus(campaign_ref)
    )
    resp = requests.get(url, params={"customer_key": customer_key})
    resp.raise_for_status()

    subscriptions = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(subscriptions))
    return subscriptions


def coop_ws_valid_events(events, date, hour=12):
    events = {e["type"]: parse_ws_date(e["ts"]) for e in events}
    dt = datetime.datetime(date.year, date.month, date.day, hour=hour)
    if "optin" not in events or events["optin"] >= dt:
        return False
    if "optout" in events and events["optout"] < dt:
        return False
    return True


def coop_human_readable_important_events(events, dt_format):
    if not events:
        return _("No important subscription events")

    result = "" if len(events) == 1 else _("%d subscription events:\n")

    for num, event in enumerate(events):
        if num:
            result += u"\n\n"
        ctx = {
            "key": event["customer_key"],
            "validity": u" >> ".join(
                sorted(format_ws_date(e["ts"], dt_format) for e in event["events"])
            ),
            "details": _hr_details(event["details"], dt_format),
        }
        result += (
            _(
                "Validity: %(validity)s\n"
                "--\n"
                "Key: %(key)s\n"
                "--\n"
                "Details:\n%(details)s\n"
            )
            % ctx
        )
    return result


def coop_ws_subscriptions(base_url, campaign_ref, customer_key):
    "Query the cooperative web services to list customer subscriptions"

    _logger.debug(
        u"Querying details %s, campaign %s, identifier %s",
        base_url,
        campaign_ref,
        customer_key,
    )

    url = base_url + "/campaign/%s/subscriptions" % urllib.parse.quote_plus(
        campaign_ref
    )
    resp = requests.get(url, params={"customer_key": customer_key})
    resp.raise_for_status()

    subscriptions = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(subscriptions))
    return subscriptions


def coop_human_readable_subscriptions(subscriptions, dt_format):
    if not subscriptions:
        return _("No subscription at all (to any partner)")

    result = []

    for i, sub in enumerate(subscriptions):
        member = sub["member"]["login"]
        if not i:
            missing = sorted(
                m["login"] for m in sub["campaign"]["members"] if m["login"] != member
            )
        result.append(
            _("Subscription to %(member)s: %(optinout)s")
            % {
                "member": member,
                "optinout": _hr_optin_out(sub["optin_ts"], sub["optout_ts"], dt_format),
            }
        )

    if subscriptions:
        result.append(_("No subscription to %s.") % u",".join(missing))

    return u"\n".join(result)


def parse_ws_date(str_date):
    "Return a timezone naive UTC date from given str_date"
    _date = iso8601.parse_date(str_date)
    return _date.replace(tzinfo=None) - _date.utcoffset()


def format_ws_date(str_date, dt_format):
    return parse_ws_date(str_date).strftime(dt_format)


def _hr_optin_out(optin_ts, optout_ts, dt_format):
    result = format_ws_date(optin_ts, dt_format)
    if optout_ts:
        result += " > " + format_ws_date(optout_ts, dt_format)
    return result


def _hr_details(subscription_details, dt_format):
    result = []
    for member, details in subscription_details.items():
        if "optin_ts" not in details:
            result.append(_("not subscribed"))
        else:
            _optinout = _hr_optin_out(
                details["optin_ts"], details["optout_ts"], dt_format
            )
            result.append(u"- %s: %s" % (member, _optinout))
    return u"\n".join(result)


class Coupon(models.Model):
    _inherit = "coupon.coupon"

    def _action_coop_prerequisites(self):
        self.ensure_one()

        campaign = self.campaign_id
        if not campaign.is_coop_campaign:
            raise UserError(_("Not a cooperative campaign!"))

        partner = self.used_for_sale_id.partner_id
        key = campaign.coop_partner_identifier(partner)

        if not key:
            raise UserError(_("Partner (%s) has no valid key.") % partner.name)
        return partner, key

    @api.multi
    def action_coop_campaign_optin_status(self):
        partner, key = self._action_coop_prerequisites()
        campaign = self.campaign_id
        base_url = self.env["ir.config_parameter"].get_param(
            "commown_cooperative_campaign.base_url"
        )

        response = [
            _("Subscription status for %(partner)s is: %(result)s"),
            u"%(details)s",
        ]
        ctx = {"partner": partner.name}
        lang = self.env["res.lang"].search([("code", "=", self.env.user.lang)])

        subscriptions = coop_ws_important_events(base_url, campaign.name, key)

        is_valid = subscriptions and coop_ws_valid_events(
            subscriptions[0]["events"], datetime.datetime.today()
        )

        if is_valid:
            ctx.update(
                {
                    "details": coop_human_readable_important_events(
                        subscriptions, lang.date_format + " " + lang.time_format
                    ),
                    "result": _("fully subscribed"),
                }
            )

        else:
            # Has incomplete subscriptions?
            subscriptions = coop_ws_subscriptions(base_url, campaign.name, key)
            ctx.update(
                {
                    "details": coop_human_readable_subscriptions(
                        subscriptions, lang.date_format + " " + lang.time_format
                    ),
                    "result": _("not fully subscribed"),
                }
            )
            response.append(_("Key: %(key)s") % {"key": key})

        raise UserError(u"\n--\n".join(response) % ctx)

    @api.multi
    def action_coop_campaign_optin_now(self):
        view = self.env.ref("commown_cooperative_campaign." "wizard_late_optin_form")
        return {
            "type": "ir.actions.act_window",
            "src_model": "coupon.coupon",
            "res_model": "coupon.late.optin.wizard",
            "name": _("Cooperative campaign late optin"),
            "views": [(view.id, "form")],
            "target": "new",
            "context": {"default_coupon_id": self.id},
        }


class Campaign(models.Model):
    _inherit = "coupon.campaign"

    is_coop_campaign = fields.Boolean(
        string="Cooperative campaign",
        help=(
            "If true, the coupon-related discount condition will use the"
            " cooperative web services to check its validity."
        ),
        index=True,
        default=False,
    )

    cooperative_salt = fields.Char(
        invisible=True,
        copy=False,
        help="Salt used to create a cooperative identifier from partner data",
    )

    @api.multi
    def coop_partner_identifier(self, partner):
        """Returns given partner's identifier for current cooperative campaign

        ... or none if the campaign is not cooperative or the identifier cannot
        be computed.
        """
        self.ensure_one()

        if not self.is_coop_campaign:
            return None

        country_code = partner.country_id.code
        if not country_code:
            return None

        if not self.cooperative_salt:
            # Should never occur, this is purely defensive code
            # This avoids a crash that could have quite some consequences
            # like not validating a sale, as this method is triggered by
            # contract date_end changes.
            _logger.error("Cooperative campaign %d has no salt set", self.id)
            return None

        for phone_num in (partner.mobile, partner.phone):
            if phone_num:
                phone_obj = phonenumbers.parse(phone_num, country_code)
                if phonenumbers.number_type(phone_obj) == MOBILE_TYPE:
                    phone = phonenumbers.format_number(
                        phone_obj, phonenumbers.PhoneNumberFormat.NATIONAL
                    ).replace(" ", "")
                    hash = hashlib.sha256()
                    hash.update((phone + self.cooperative_salt).encode("utf-8"))
                    return hash.hexdigest()
