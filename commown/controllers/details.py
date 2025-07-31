import logging

from odoo import http

from odoo.addons.commown_administrative_docs.controllers import details

_logger = logging.getLogger(__name__)


class CommownCustomerPortal(details.AdminDocsCustomerPortal):
    MANDATORY_BILLING_FIELDS = [
        field
        for field in details.AdminDocsCustomerPortal.MANDATORY_BILLING_FIELDS
        if field != "name"
    ] + ["firstname", "lastname", "zipcode"]

    OPTIONAL_BILLING_FIELDS = (
        details.AdminDocsCustomerPortal.OPTIONAL_BILLING_FIELDS
        + [
            "street2",
            "state_id",
        ]
    )

    def details_form_validate(self, data):
        """Add Slimpay validation of submitted partner data"""
        error, error_message = super().details_form_validate(data)
        partner_model = http.request.env["res.partner"]
        values = {key: data[key] for key in self.MANDATORY_BILLING_FIELDS}
        values.update(
            {key: data[key] for key in self.OPTIONAL_BILLING_FIELDS if key in data}
        )
        values.update({"zip": values.pop("zipcode", "")})
        for attribute, message in partner_model.slimpay_checks(values).items():
            error[attribute] = "error"
            error_message.append(message)

        partner_model.validate_street_lines(data, error, error_message)

        return error, error_message
