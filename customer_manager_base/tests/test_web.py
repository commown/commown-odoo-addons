from odoo.tests.common import tagged

from odoo.addons.commown_allow_backend_passage.tests.test_web import (
    BackendPassageControllerTC,
)


@tagged("-at_install", "post_install")
class CustomerManagerControllerTC(BackendPassageControllerTC):
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
