import logging

from datetime import datetime
from email.parser import Parser
from cgi import parse_header
import json
from base64 import b64decode
import re

import requests
import phonenumbers


_logger = logging.getLogger(__name__)

MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE

BASE_URL = 'https://ws.colissimo.fr/sls-ws/SlsServiceWSRest'


class ColissimoError(Exception):
    pass


class AddressTooLong(Exception):

    def __init__(self, partner):
        self.partner = partner


def normalize_phone(phone_number, country_code):
    " Colissimo only accepts french phone numbers "
    if country_code == 'FR' and phone_number:
        tel = phonenumbers.parse(phone_number, country_code)
        return phonenumbers.format_number(
            tel, phonenumbers.PhoneNumberFormat.NATIONAL).replace(' ', '')
    return ''


def delivery_data(partner):
    """ Return delivery data for given partner, taking into account:

    - that mobile phone numbers may be found in partner.phone instead
      of partner.mobile: put value into mobile if pertinent
    - delivery contact may be specified on partner
    - delivery contact may not have a copy of partner's phones and address
    - the address lines must not be too long (35 characters was the limit on
      coliship): in such a case, raise ValueError

    """
    mobile, fixed = partner.mobile, partner.phone
    if not mobile and fixed and partner.country_id.code == 'FR':
        fixed_obj = phonenumbers.parse(fixed, 'FR')
        if phonenumbers.number_type(fixed_obj) == MOBILE_TYPE:
            mobile, fixed = fixed, None
    partner_data = {
        'lastName': partner.lastname or '',
        'firstName': partner.firstname or '',
        'line2': partner.street,
        'countryCode': partner.country_id.code or 'FR',
        'city': partner.city,
        'zipCode': partner.zip,
        'phoneNumber': normalize_phone(fixed, partner.country_id.code) or '',
        'mobileNumber': normalize_phone(mobile, partner.country_id.code) or '',
        'email': partner.email or '',
    }
    if partner.street2:
        partner_data['line1'] = partner.street
        partner_data['line2'] = partner.street2
    if partner.parent_id and partner.parent_id.is_company:
        partner_data['companyName'] = partner.parent_id.name

    delivery_id = partner.address_get(['delivery'])['delivery']
    if delivery_id == partner.id:
        result_data = partner_data
    else:
        result_data = None
        comment = partner.browse(delivery_id).comment
        if comment:
            match = re.match(r'^\[BP\] (?P<bp>[0-9]+)$', comment)
            if match:
                result_data = partner_data
                result_data['BP'] = match.groupdict()['bp']
        if result_data is None:
            result_data = delivery_data(
                partner.env['res.partner'].browse(delivery_id))
            # Add fallback contact values if not set in delivery contact:
            for attr in 'phoneNumber', 'mobileNumber', 'email', 'companyName':
                if not result_data.get(attr) and attr in partner_data:
                    result_data[attr] = partner_data[attr]

    for attr in ('line1', 'line2', 'line3'):
        if len(result_data.get(attr) or '') > 35:  # handle False and None
            raise AddressTooLong(partner)

    return result_data


def shipping_data(sender, recipient, order_number, commercial_name,
                  weight, insurance_value=0., is_return=False,
                  deposit_date=None, format='PDF_A4_300dpi'):
    """ Return colissimo WS shipping data for given arguments.

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

    The `format` argument can be one of:
    - "PDF_A4_300dpi" (the default)
    - "PDF_10x15_300dpi"
    """

    if deposit_date is None:
        deposit_date = datetime.today()

    if is_return:
        sender, recipient = recipient, sender

    sender_data = delivery_data(sender)
    recipient_data = delivery_data(recipient)

    if any(d["countryCode"] != 'FR' for d in (sender_data, recipient_data)):
        # Colissimo Export/ Return International
        product_code = 'COLI' if not is_return else 'CORI'
    else:
        product_code = 'DOS' if not is_return else 'CORE'

    service = {
        'orderNumber': order_number,  # for coliview
        'productCode': product_code,
        'depositDate': deposit_date.strftime('%Y-%m-%d'),
        'commercialName': commercial_name,
    }

    parcel = {'weight': weight,
              'insuranceValue': int(insurance_value * 100)}

    return {
        'outputFormat': {
            'x': 0,
            'y': 0,
            'outputPrintingType': format,
            # 'outputPrintingType': 'PDF_10x15_300dpi',  # cf. doc p27
        },
        'letter': {
            'service': service,
            'parcel': parcel,
            'sender': {
                'senderParcelRef': order_number,     # visible on the label
                'address': sender_data,
            },
            'addressee': {
                'addresseeParcelRef': order_number,  # visible on the label
                'address': recipient_data,
            }
        }
    }


def parse_multipart(data, boundary):
    # Build a fake email to use email module's multipart parser
    headers = ['From: contact@commown.fr',
               'To: contact@commown.fr',
               'Subject: colissimo',
               'MIME-Version: 1.0',
               'Content-Type: multipart/mixed; ',
               '\tboundary="%s"' % boundary,
               '',
               '',
               ]
    msg = Parser().parsestr('\r\n'.join(headers) + data)

    meta_data, label_data = None, None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype.startswith('application/json'):
            meta_data = json.loads(part.get_payload())
        elif ctype.startswith('application/octet-stream'):
            label_data = part.get_payload()
            if part['Content-Transfer-Encoding'] == 'base64':
                label_data = b64decode(label_data)
    return meta_data, label_data


def parse_response(resp):
    ctype_main, ctype_details = parse_header(resp.headers['Content-Type'])
    if ctype_main == 'multipart/mixed':
        return parse_multipart(resp.content, ctype_details['boundary'])
    elif ctype_main == 'application/json':
        return resp.json(), None
    return None, None


def ship(login, password, debug=False, **kwargs):
    url = BASE_URL + ('/checkGenerateLabel' if debug else '/generateLabel')
    data = shipping_data(**kwargs)
    data.update({'contractNumber': login, 'password': password})
    _logger.debug('Shipping data: %s', data)
    resp = requests.post(url, json=data)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        # Try to decode the response error:
        err, _tmp = parse_response(resp)
        if err is not None:
            msg = err['messages'][0]['messageContent']
            _logger.error('Colissimo error. Response text is:\n%s', msg)
            raise ColissimoError(msg)
        # But give-up in case of unexpected output
        else:
            _logger.error('Colissimo error content:\n%r', resp.content)
            raise

    return parse_response(resp)
