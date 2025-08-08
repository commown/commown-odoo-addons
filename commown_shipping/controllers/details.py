from odoo import http

from odoo.addons.portal.controllers.portal import CustomerPortal


class CommownShippingCustomerPortal(CustomerPortal):
    OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + [
        "street2",
        "state_id",
    ]

    def details_form_validate(self, data):
        """Add Colissimo address validation to submitted partner data"""
        error, error_message = super().details_form_validate(data)
        partner_model = http.request.env["res.partner"]
        partner_model.validate_street_lines(data, error, error_message)

        return error, error_message
