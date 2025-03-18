import phonenumbers

MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE
FORMAT_DICT = {
    "national": phonenumbers.PhoneNumberFormat.NATIONAL,
    "international": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
}


def normalize_phone(
    phone_number, country_code, number_format="international", raise_on_error=True
):
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
            return phonenumbers.format_number(tel, FORMAT_DICT[number_format]).replace(
                " ", ""
            )
    return ""


def is_mobile(phone_number, country):
    return (
        phonenumbers.number_type(phonenumbers.parse(phone_number, country))
        == MOBILE_TYPE
    )
