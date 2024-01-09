import json
import logging
from cgi import parse_header
from datetime import datetime

import phonenumbers
import requests
from requests_toolbelt.multipart import decoder

from odoo import _

_logger = logging.getLogger(__name__)

MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE

BASE_URL = "https://ws.colissimo.fr/sls-ws/SlsServiceWSRest"

MAX_ADDRESS_SIZE_COLISSIMO = 35


class ColissimoError(Exception):
    pass


def normalize_phone(phone_number, country_code, raise_on_error=True):
    """Format phone number for Colissimo

    If phone number format is incorrect, raise if raise_on_error is True (default)
    else return the empty string.

    If the phone number is falsy, return the empty string.
    """
    if phone_number:
        try:
            tel = phonenumbers.parse(phone_number, country_code)
        except phonenumbers.NumberParseException:
            if raise_on_error:
                raise
        else:
            return phonenumbers.format_number(
                tel, phonenumbers.PhoneNumberFormat.NATIONAL
            ).replace(" ", "")
    return ""


def delivery_data(partner, raise_on_error=True):
    """Return delivery data for given partner, taking into account:

    - that mobile phone numbers may be found in partner.phone instead
      of partner.mobile: put value into mobile if pertinent
    - the address lines must not be too long (35 characters was the limit on
      coliship): in such a case, raise ValueError
    - at least one phone number is required to ease delivery
    - an email is required to get a delivery notification

    If raise_on_error is False, never raise and replace invalid phone numbers
    by the empty string in the result.
    """

    country = partner.country_id.code or "FR"

    mobile = normalize_phone(partner.mobile, country, raise_on_error)
    fixed = normalize_phone(partner.phone, country, raise_on_error)

    if not mobile and fixed:
        fixed_obj = phonenumbers.parse(partner.phone, partner.country_id.code)
        if phonenumbers.number_type(fixed_obj) == MOBILE_TYPE:
            mobile, fixed = fixed, ""

    partner_data = {
        "lastName": partner.lastname or "",
        "firstName": partner.firstname or "",
        "line2": partner.street,
        "countryCode": country,
        "city": partner.city,
        "zipCode": partner.zip,
        "phoneNumber": fixed,
        "mobileNumber": mobile,
        "email": partner.email or "",
    }

    if partner.street2:
        partner_data["line1"] = partner.street
        partner_data["line2"] = partner.street2

    if partner.parent_id and partner.parent_id.is_company:
        partner_data["companyName"] = partner.parent_id.name

    if raise_on_error and not (
        partner_data["phoneNumber"] or partner_data["mobileNumber"]
    ):
        raise ColissimoError(
            _("A phone number is required to generate a Colissimo label!")
        )

    if raise_on_error and not partner_data["email"]:
        raise ColissimoError(_("An email is required to generate a Colissimo label!"))

    return partner_data


def shipping_data(
    sender,
    recipient,
    order_number,
    commercial_name,
    weight,
    insurance_value=0.0,
    is_return=False,
    deposit_date=None,
    label_format="PDF_A4_300dpi",
):
    """Return colissimo WS shipping data for given arguments.

    The `sender` and `recipient` are odoo res.partner objects.

    The `order_number` argument is a string displayed on the label (on both
    sender and recipient parts).

    The `commercial_name` argument is used in recipient email notifications.

    The `weight` argument is the parcel weight in kg.

    The `insurance_value` argument is the insurance value in euro
    (None, the default value, means no insurance).

    The `is_return` argument is used to indicate the parcel is sent back from
    the recipient to the sender.

    The `deposit_date` argument is a datetime.Date object (default is today).

    The `label_format` argument can be one of:
    - "PDF_A4_300dpi" (the default)
    - "PDF_10x15_300dpi"
    """

    if deposit_date is None:
        deposit_date = datetime.today()

    if is_return:
        sender, recipient = recipient, sender

    sender_data = delivery_data(sender)
    recipient_data = delivery_data(recipient)

    if any(d["countryCode"] != "FR" for d in (sender_data, recipient_data)):
        # Colissimo Export/ Return International
        product_code = "COLI" if not is_return else "CORI"
    else:
        product_code = "DOS" if not is_return else "CORE"

    service = {
        "orderNumber": order_number,  # for coliview
        "productCode": product_code,
        "depositDate": deposit_date.strftime("%Y-%m-%d"),
        "commercialName": commercial_name,
    }

    if product_code == "COLI":
        service["returnTypeChoice"] = 3  # cf. doc p. 31 - no return if undelivered

    parcel = {"weight": weight, "insuranceValue": int(insurance_value * 100)}

    return {
        "outputFormat": {
            "x": 0,
            "y": 0,
            "outputPrintingType": label_format,
            # 'outputPrintingType': 'PDF_10x15_300dpi',  # cf. doc p27
        },
        "letter": {
            "service": service,
            "parcel": parcel,
            "sender": {
                "senderParcelRef": order_number,  # visible on the label
                "address": sender_data,
            },
            "addressee": {
                "addresseeParcelRef": order_number,  # visible on the label
                "address": recipient_data,
            },
        },
    }


def parse_multipart(http_resp):

    multipart_data = decoder.MultipartDecoder.from_response(http_resp)

    meta_data, label_data = None, None
    for part in multipart_data.parts:
        ctype = part.headers[b"Content-Type"]
        if ctype.startswith(b"application/json"):
            meta_data = json.loads(part.text)
        elif ctype.startswith(b"application/octet-stream"):
            label_data = part.content
    return meta_data, label_data


def parse_response(resp):
    ctype_main, _ctype_details = parse_header(resp.headers["Content-Type"])
    if ctype_main == "multipart/mixed":
        return parse_multipart(resp)
    elif ctype_main == "application/json":
        return resp.json(), None
    return None, None


def ship(login, password, debug=False, **kwargs):
    url = BASE_URL + ("/checkGenerateLabel" if debug else "/generateLabel")
    data = shipping_data(**kwargs)
    data.update({"contractNumber": login, "password": password})
    _logger.debug("Shipping data: %s", data)
    resp = requests.post(url, json=data)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        # Try to decode the response error:
        err, _tmp = parse_response(resp)
        if err is not None:
            msg = err["messages"][0]["messageContent"]
            _logger.error("Colissimo error. Response text is:\n%s", msg)
            raise ColissimoError(msg)
        # But give-up in case of unexpected output
        else:
            _logger.error("Colissimo error content:\n%r", resp.content)
            raise

    return parse_response(resp)
