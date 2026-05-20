from lxml import html

from odoo.tests import HttpCase


def slogan_text(html_string):
    return html.fromstring(html_string).xpath("//*[@data-name='Slogan']/text()")


class CommownWebsiteDesignTC(HttpCase):
    def test_custom_slogans_in_header_template(self):
        """
        When selecting the Slogan Header template, our views with our customs Slogans should be used
        """
        # Setup
        website = self.env.ref("website.default_website")
        website_b2b = self.env.ref("website_b2b.b2b_website")
        theme_utils = self.env["theme.utils"]

        tmpl_key = "website.template_header_slogan"

        # We authenticate as a user possessing the groups required to use the /website/force/ endpoint
        self.authenticate("demo", "demo")

        # Default state: there shouldn't be a Slogan in the view
        default_res = self.url_open("/")
        self.assertFalse(slogan_text(default_res.text))

        # Setting the Slogan Header, on both sites we use
        theme_utils.with_context(website_id=website.id).enable_view(tmpl_key)
        theme_utils.with_context(website_id=website_b2b.id).enable_view(tmpl_key)

        res_b2c = self.url_open("/")
        res_b2b = self.url_open(f"/website/force/{website_b2b.id}")

        self.assertEqual(slogan_text(res_b2c.text), ["Commown pour les particuliers"])
        self.assertEqual(slogan_text(res_b2b.text), ["Commown pour les professionnels"])

    def test_contact_page_to_showcase_site_redirect(self):
        res = self.url_open("/contactus", allow_redirects=False)

        self.assertTrue(res.is_redirect)
        self.assertEqual(res.headers["Location"], "https://commown.coop/#contact")
