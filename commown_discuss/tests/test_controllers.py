from odoo.tests import HttpCase


class CommownDiscussControllersTC(HttpCase):
    def test_portal_users_with_channels(self):
        "Users subscribed to mail.channels should be able to access the backend"
        channel = self.env["mail.channel"].create(
            {"name": "Dummy Mail Channel", "channel_type": "group"}
        )
        partner = self.env.ref("base.partner_demo_portal")

        self.authenticate("portal", "portal")

        # Case 1: the user is not subscribed to any mail channels
        resp_no_chans = self.url_open(self.base_url() + "/web", allow_redirects=False)

        self.assertEqual(resp_no_chans.status_code, 303)
        self.assertIn("/web/login_successful", resp_no_chans.headers["Location"])

        # Case 2: the user is subscribed to at least one mail channel
        channel.add_members(partner_ids=partner.ids)

        resp_w_chans = self.url_open(self.base_url() + "/web", allow_redirects=False)

        self.assertEqual(resp_w_chans.status_code, 200)
