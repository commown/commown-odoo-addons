from odoo import _, models

from .common import is_mobile, normalize_phone


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_mobile_phone(
        self,
        fr_as_default_country=False,
    ):
        """Return normalized mobile phone of partner if exists, return False if not.
        If fr_as_default_country is set to True, it assume France is the country when not specified"""

        if fr_as_default_country:
            country = self.country_id.code or "FR"
        else:
            country = self.country_id.code

        if not country:
            raise ValueError(
                _(
                    "the partner %s does not have a set country or the country has no associated country code. Impossible to parse his phone number"
                )
                % self.id
            )
        if self.mobile and is_mobile(self.mobile, country):
            return normalize_phone(self.mobile, country, True)
        elif self.phone and is_mobile(self.phone, country):
            return normalize_phone(self.phone, country, True)
        else:
            return False
