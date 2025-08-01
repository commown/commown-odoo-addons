import logging

from odoo.http import request

from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)


class CommownAuthSignup(AuthSignupHome):
    _commown_signup_auth_keys = ("firstname", "lastname")

    def _prepare_signup_values(self, qcontext):
        """
        Add firstname and lastname compatibility to the auth_signup module

        The original controller retrieves every key in SIGN_UP_REQUEST_PARAMS,
        then drops all keys of the qweb context but login, name and password.
        We compute a `name` because `res_user` `_signup_create_user` methods
        asserts one is supplied.

        """
        qcontext.update(
            {key: request.params.get(key) for key in self._commown_signup_auth_keys}
        )

        if qcontext.get("name") is None:
            Partner = request.env["res.partner"]
            qcontext["name"] = Partner._get_computed_name(
                qcontext["lastname"], qcontext["firstname"]
            )

        return super()._prepare_signup_values(qcontext)
