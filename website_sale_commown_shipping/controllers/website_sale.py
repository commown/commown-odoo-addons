from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class CommownShippingWebsiteSaleController(WebsiteSale):
    def _get_mandatory_fields_shipping(self, country_id=False):
        fields = super()._get_mandatory_fields_shipping(country_id=country_id)
        if "email" not in fields:
            fields.append("email")
        return fields

    def checkout_form_validate(self, mode, all_form_values, data):
        errors, messages = super().checkout_form_validate(mode, all_form_values, data)
        http.request.env["res.partner"].validate_street_lines(data, errors, messages)
        return errors, messages
