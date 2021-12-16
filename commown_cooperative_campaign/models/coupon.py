import hashlib

import phonenumbers

from odoo import models, fields, api


MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE


def mobile_phone(partner, restrict_to_country_code=None):
    country_code = partner.country_id.code
    if country_code and (restrict_to_country_code is None
                         or country_code == restrict_to_country_code):
        for phone_num in (partner.mobile, partner.phone):
            if phone_num:
                phone_obj = phonenumbers.parse(phone_num, country_code)
                if phonenumbers.number_type(phone_obj) == MOBILE_TYPE:
                    return phonenumbers.format_number(
                        phone_obj, phonenumbers.PhoneNumberFormat.NATIONAL
                    ).replace(' ', '')


class Campaign(models.Model):
    _inherit = "coupon.campaign"

    is_coop_campaign = fields.Boolean(
        string="Cooperative campaign",
        help=("If true, the coupon-related discount condition will use the"
              " cooperative web services to check its validity."),
        index=True,
        default=False)

    @api.multi
    def coop_partner_identifier(self, partner):
        """ Returns given partner's identifier for current cooperative campaign

        ... or none if the campaign is not cooperative or the identifier cannot
        be computed.
        """
        self.ensure_one()

        if not self.is_coop_campaign:
            return None

        phone = mobile_phone(partner, u"FR")
        if phone is not None:
            acc = self.env["keychain.account"].search([
                ("technical_name", "=", self.name + "-salt"),
            ]).ensure_one()
            hash = hashlib.sha256()
            hash.update(phone + acc._get_password())
            return hash.hexdigest()
