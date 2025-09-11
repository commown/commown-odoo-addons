from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class SlimpayControllerWebsiteSale(WebsiteSale):
    "Override address edition methods to add Slimpay-specific field constraints"

    def checkout_form_validate(self, mode, all_form_values, data):
        """Validate partner constraints wrt Slimpay's rule"""
        errors, error_msg = super().checkout_form_validate(mode, all_form_values, data)
        order = request.website.sale_get_order()
        partner = order.partner_id
        for field, msg in partner.slimpay_checks(all_form_values).items():
            errors[field] = "error"
            error_msg.append(msg)
        return errors, error_msg
