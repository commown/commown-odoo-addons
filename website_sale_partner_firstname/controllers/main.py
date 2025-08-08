import logging

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class SlimpayControllerWebsiteSale(WebsiteSale):
    "Override address edition methods to add Slimpay-specific field constraints"

    def _get_mandatory_fields_billing(self, country_id=False):
        '''Replace "name" by "firstname" and "lastname"'''
        fields = super()._get_mandatory_fields_billing(country_id=country_id)
        return ["firstname", "lastname"] + [f for f in fields if f != "name"]

    def _get_mandatory_fields_shipping(self, country_id=False):
        '''Replace "name" by "firstname" and "lastname"'''
        fields = super()._get_mandatory_fields_shipping(country_id=country_id)
        return ["firstname", "lastname"] + [f for f in fields if f != "name"]

    def values_postprocess(self, order, mode, values, errors, error_msg):
        """Do not drop firstname and lastname fields for `partner_firstname`
        module compatiblity."""
        new_values, errors, error_msg = super().values_postprocess(
            order, mode, values, errors, error_msg
        )
        for field in ("firstname", "lastname"):
            if field in values:
                _logger.debug(
                    "payment_slimpay postprocess: %s value has finally *not* "
                    "been dropped.",
                    field,
                )
                new_values[field] = values[field]
        return new_values, errors, error_msg
