import logging
import hashlib

import phonenumbers

from odoo import models, fields, api


MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE


_logger = logging.getLogger(__file__)


class Campaign(models.Model):
    _inherit = "coupon.campaign"

    is_coop_campaign = fields.Boolean(
        string="Cooperative campaign",
        help=("If true, the coupon-related discount condition will use the"
              " cooperative web services to check its validity."),
        index=True,
        default=False)

    cooperative_salt = fields.Char(
        invisible=True,
        copy=False,
        help="Salt used to create a cooperative identifier from partner data")

    @api.multi
    def coop_partner_identifier(self, partner):
        """ Returns given partner's identifier for current cooperative campaign

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
                    ).replace(' ', '')
                    hash = hashlib.sha256()
                    hash.update((phone + self.cooperative_salt).encode('utf-8'))
                    return hash.hexdigest()
