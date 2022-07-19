import logging
from base64 import b64encode

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal

from odoo.addons.commown.models.res_partner import FileTooBig


_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    MANDATORY_BILLING_FIELDS = [
        "firstname",
        "lastname",
        "phone",
        "email",
        "street",
        "zipcode",
        "city",
        "country_id",
    ]
    OPTIONAL_BILLING_FIELDS = [
        "id_card1",
        "id_card2",
        "proof_of_address",
        "state_id",
    ]

    def details_form_validate(self, data):
        """ Add Slimpay validation of submitted partner data """
        error, error_message = super(CustomerPortal, self).details_form_validate(data)
        Partner = http.request.env["res.partner"]
        values = {key: data[key] for key in self.MANDATORY_BILLING_FIELDS}
        values.update(
            {key: data[key] for key in self.OPTIONAL_BILLING_FIELDS if key in data}
        )
        values.update({"zip": values.pop("zipcode", "")})
        for attribute, message in Partner.slimpay_checks(values).items():
            error[attribute] = "error"
            error_message.append(message)
        try:
            Partner._apply_bin_field_size_policy(values)
        except FileTooBig as exc:
            error[exc.field] = "error"
            error_message.append(exc.msg)
        return error, error_message

    @http.route()
    def account(self, redirect=None, **post):
        if post:
            partner = http.request.env.user.partner_id
            _logger.debug("details posted: %s", post)
            for field in partner.auto_widget_binary_fields:
                if post.get(field):
                    if not post[field].filename:
                        post[field] = False
                    else:
                        post[field] = b64encode(post[field].read())
        return super(CustomerPortal, self).account(redirect=redirect, **post)
