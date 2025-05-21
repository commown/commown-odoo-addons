from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class CustomerManagerControllerTC(HttpCase):
    timeout = 12

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = cls.env.ref("base.user_demo")
        cls.portal_user = cls.env.ref("base.demo_user0")

    def get(
        self,
        url,
        data=None,
        json=None,
        headers=None,
        allow_redirects=False,
        assert_code=200,
    ):
        """Perform a GET http request using requests. Complements HttpCase.url_open
        with headers and json"""
        if url.startswith("/"):  # pragma: no cover
            url = self.base_url() + url
        resp = self.opener.get(
            url,
            data=data,
            json=json,
            timeout=self.timeout,
            headers=headers,
            allow_redirects=allow_redirects,
        )
        self.assertEqual(assert_code, resp.status_code)
        return resp

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

    def test_customer_admin_user(self):
        # Check redirect for non-customer admin portal user
        self.authenticate("portal", "portal")
        non_customer_admin_res = self.get("/web", assert_code=303)
        self.assertEqual(
            non_customer_admin_res.headers["location"],
            self.base_url() + "/web/login_successful",
        )

        # Check /web access for customer admin portal user
        self.portal_user.groups_id |= self.env.ref(
            "customer_manager_base.group_customer_admin"
        )
        customer_admin_res = self.get("/web")
        self.assertEqual(
            customer_admin_res.url,
            self.base_url() + "/web",
        )

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
