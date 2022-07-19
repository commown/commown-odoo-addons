import lxml.html
from mock import patch

from odoo.addons.website.models.website import Website  # see mock

from odoo import api
from odoo.addons.website.tools import MockRequest

from .common import RentalSaleOrderTC


def _clean_text(node):
    return " ".join(t.strip() for t in node.itertext() if t.strip())


class WebsiteTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        partner = self.env.ref("base.partner_demo_portal")
        self.so = self.create_sale_order(partner)
        self.so.action_confirm()
        # Use a portal user to avoid language selector rendering
        # (other page is editable and the selector is more complex)
        env = api.Environment(self.env.cr, partner.user_ids[0].id, {})
        self.website = self.env.ref("website.default_website").with_env(env)
        self.contracts = self.env["contract.contract"].search(
            [
                ("name", "ilike", "%" + self.so.name + "%"),
            ]
        )

    def render_view(self, ref, **render_kwargs):
        view = self.env.ref(ref)
        with patch.object(Website, "get_alternate_languages", return_value=()):
            with MockRequest(self.env, website=self.website) as request:
                request.httprequest.args = []
                request.httprequest.query_string = u""
                request.endpoint_arguments = {}
                html = view.render(render_kwargs)
        return lxml.html.fromstring(html)

    def test_portal_sale_order_view(self):
        doc = self.render_view(
            "sale.sale_order_portal_template", sale_order=self.so, website=self.website
        )
        product_names = map(_clean_text, doc.xpath("//td[@id='product_name']"))
        self.assertEqual(
            list(product_names),
            [
                "Fairphone Premium (deposit)",
                "PC (deposit)",
                "GS Headset",
                "FP2 (deposit)",
                "headset (deposit)",
                "screen (deposit)",
                "keyboard (deposit)",
                "keyboard deluxe (deposit)",
            ],
        )

    def test_portal_contract_view(self):
        doc = self.render_view(
            "contract.portal_contract_page",
            page_name="Contracts",
            contract=self.contracts[0],
            website=self.website,
        )
        self.assertEqual(
            doc.xpath("//div[@id='general_information']//h6//text()"), ["Customer:"]
        )  # Responsible was removed from original view
        self.assertFalse(
            doc.xpath(
                "//section[contains(concat(' ',normalize-space(@class),' '),"
                "' s_timeline ')]"
            )
        )
