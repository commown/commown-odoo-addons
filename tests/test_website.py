import lxml.html

from odoo.addons.website.tools import MockRequest

from .common import RentalSaleOrderTC


def _clean_text(node):
    return ' '.join(t.strip() for t in node.itertext() if t.strip())


class WebsiteTC(RentalSaleOrderTC):

    def test_portal_sale_order_view(self):
        partner = self.env.ref('base.res_partner_3')
        so = self.create_sale_order(partner)
        so.action_confirm()

        website = self.env.ref('website.default_website')
        view = self.env.ref('sale.sale_order_portal_template')

        with MockRequest(self.env, website=website) as request:
            request['httprequest']['args'] = []
            request.csrf_token = lambda *args: 'token'
            html = view.render({
                'sale_order': so,
                'website': website,
                'main_object': (),
            })

        with open('/tmp/sale_order.html', 'wb') as fobj:  # XXX remove me
            fobj.write(html)

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
