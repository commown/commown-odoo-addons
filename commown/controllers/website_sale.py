from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class CommownControllerWebsiteSale(WebsiteSale):
    def _get_mandatory_shipping_fields(self):
        fields = super()._get_mandatory_billing_fields()
        if "email" not in fields:
            fields.append("email")
        return fields

    def checkout_form_validate(self, mode, all_form_values, data):
        errors, messages = super().checkout_form_validate(mode, all_form_values, data)
        http.request.env["res.partner"].validate_street_lines(data, errors, messages)
        return errors, messages
