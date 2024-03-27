from odoo import _, models

from .common import is_mobile


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_mobile_phone(self):
        """Return normalized mobile phone of partner if exists, return False if not.
        Raise an error if a country cannot be foud"""

        country = (
            self.country_id.code
            or self.env["res.company"]._company_default_get().country_id.code
        )

        if not country:
            raise ValueError(
                _(
                    "The partner %s does not have a set country or the country has no associated country code. Impossible to parse his phone number"
                )
                % self.id
            )
        if self.mobile and is_mobile(self.mobile, country):
            return self.mobile
        elif self.phone and is_mobile(self.phone, country):
            return self.phone
        else:
            return False
