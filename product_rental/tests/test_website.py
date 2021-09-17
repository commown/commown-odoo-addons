import lxml.html

from odoo.addons.website.tools import MockRequest

from .common import RentalSaleOrderTC


def _clean_text(node):
    return ' '.join(t.strip() for t in node.itertext() if t.strip())


class WebsiteTC(RentalSaleOrderTC):

    def setUp(self):
        super().setUp()
        partner = self.env.ref('base.res_partner_3')
        self.so = self.create_sale_order(partner)
        self.so.action_confirm()
        self.website = self.env.ref('website.default_website')
        self.contracts = self.env['contract.contract'].search([
            ('name', 'ilike', '%' + self.so.name + '%'),
            ])

    def test_portal_sale_order_view(self):
        view = self.env.ref('sale.sale_order_portal_template')

        with MockRequest(self.env, website=self.website) as request:
            request['httprequest']['args'] = []
            request.csrf_token = lambda *args: 'token'
            html = view.render({
                'sale_order': self.so,
                'website': self.website,
                'main_object': (),
            })

        doc = lxml.html.fromstring(html)
        product_names = map(_clean_text, doc.xpath("//td[@id='product_name']"))
        self.assertEqual(list(product_names), [
            'Fairphone Premium (deposit)',
            'PC (deposit)',
            'GS Headset',
            'FP2 (deposit)',
            'headset (deposit)',
            'screen (deposit)',
            'keyboard (deposit)',
            'keyboard deluxe (deposit)',
        ])

    def test_portal_contract_view(self):
        contract = self.contracts[0]
        view = self.env.ref('contract.portal_contract_page')

        with MockRequest(self.env, website=self.website) as request:
            request['httprequest']['args'] = []
            request.csrf_token = lambda *args: 'token'
            html = view.render({
                "page_name": "Contracts",
                "contract": contract,
                'website': self.website,
                'main_object': (),
            })

        doc = lxml.html.fromstring(html)
        self.assertEqual(
            doc.xpath("//div[@id='general_information']//h6//text()"),
            ['Customer:'])  # Responsible was removed from original view
        self.assertFalse(doc.xpath(
            "//section[contains(concat(' ',normalize-space(@class),' '),"
            "' s_timeline ')]"))
