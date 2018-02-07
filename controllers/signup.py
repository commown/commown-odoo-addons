import logging

from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request

_logger = logging.getLogger(__name__)


class CommownAuthSignup(AuthSignupHome):

    _commown_signup_auth_keys = ('firstname', 'lastname')

    def do_signup(self, qcontext):
        """Add firstname and lastname compatibility to the auth_signup module

        The original controller drops all key of the qweb context but
        login, name and password. We compute a `name` because
        `res_user` `_signup_create_user` methods asserts one is
        supplied.

        """
        values = {
            key: qcontext.get(key)
            for key in ('login', 'password') + self._commown_signup_auth_keys}
        assert values.get('password') == qcontext.get('confirm_password'), \
            "Passwords do not match; please retype them."
        if qcontext.get('name') is None:
            Partner = request.env['res.partner']
            values['name'] = Partner._get_computed_name(
                values['lastname'], values['firstname'])
        else:
            values['name'] = qcontext['name']
        for lang in request.env['res.lang'].sudo().search_read([], ['code']):
            if request.lang == lang['code']:
                values['lang'] = request.lang
                break
        _logger.debug('signup values: %s', values)
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()
