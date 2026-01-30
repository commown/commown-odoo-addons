from unittest.mock import patch

from odoo.service import security
from odoo.tests.common import tagged

from odoo.addons.commown_allow_backend_passage.controllers import web

from .common import BackendPassageTC


@tagged("-at_install", "post_install")
class BackendPassageControllerTC(BackendPassageTC):
    # Main routes
    def test_no_user(self):
        # Checking redirect if no user is logged on
        no_user_res = self.get("/web", assert_code=303)
        self.assertEqual(
            no_user_res.headers["location"],
            self.base_url() + "/web/login",
        )

    def test_internal_user(self):
        # Check /web access after logging on for internal user
        self.authenticate("demo", "demo")

        internal_user_res = self.get("/web")
        self.assertEqual(
            internal_user_res.url,
            self.base_url() + "/web",
        )

    def test_portal_user(self):
        "Check /web access for a portal user, if they're allowed or not to access the backend"
        self.authenticate("portal", "portal")

        # Case 1: the user doesn't meet the criteria for backend passage
        not_allowed_user_res = self.get("/web", assert_code=303)
        self.assertTrue(not_allowed_user_res.is_redirect)
        self.assertEqual(
            not_allowed_user_res.headers["location"],
            self.base_url() + "/web/login_successful",
        )

        # Case 2: the user meets the criteria for backend passage
        with patch.object(web.Home, "allow_backend_passage", return_value=True):
            allowed_user_res = self.get("/web")

        self.assertFalse(allowed_user_res.is_redirect)

    # Misc. routes
    def test_access_with_redirect(self):
        self.authenticate("demo", "demo")
        redirected_res = self.get(
            "/web", data={"redirect": "/redirected"}, assert_code=303
        )

        self.assertEqual(
            redirected_res.headers["location"],
            self.base_url() + "/redirected",
        )

    def test_session_expired(self):
        """
        Checking 'session expiry' when the session token is invalid.

        To check if the session is invalid, the /web controller calls
        the check_session method, to compare the session token calculated
        from the user data, and the actual session token.

        However, since check_session is also called before the controller,
        We replicate a failure in the controller by using a mock.
        """
        calls = []

        # pylint: disable=dangerous-default-value
        def check_session_mock(*args, calls=calls, **kwargs):
            """
            This function is called twice server-side when :
            1. Authenticating the user (needs to be True)
            2. Checking if the session expired in the controller
            (needs to be False to emulate session expiry)

            So, on the first call, we return True, and on following calls, we return False
            """
            calls.append(1)
            return len(calls) <= 1

        self.authenticate("admin", "admin")

        with patch.object(security, "check_session", new=check_session_mock):
            # An invalidated session redirects the user to the login screen.
            expired_res = self.get("/web", assert_code=303)
            self.assertIn(
                self.base_url() + "/web/login",
                expired_res.headers["location"],
            )

        self.assertEqual(len(calls), 2)
