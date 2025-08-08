import lxml.html

from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class WebsiteSaleControllerTC(HttpCase):
    timeout = 12  # Use much bigger values for interactive debugging

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

    def post(self, url, data=None, json=None, headers=None, assert_code=200):
        """POST an http request using requests. Complements HttpCase.url_open
        with headers and json"""
        if url.startswith("/"):  # pragma: no cover
            url = self.base_url() + url
        resp = self.opener.post(
            url, data=data, json=json, timeout=self.timeout, headers=headers
        )
        self.assertEqual(assert_code, resp.status_code)
        return resp.text if json is None else resp.json()

    def csrf_token(self, html_text):
        doc = lxml.html.fromstring(html_text)
        return doc.xpath("//input[@name='csrf_token']")[0].get("value")

    def add_product_to_user_cart(self):
        product = self.env.ref("product.product_delivery_02_product_template")
        csrf_token = self.csrf_token(
            self.url_open(product.website_url, timeout=self.timeout).text
        )
        self.post(
            "/shop/cart/update",
            data={
                "product_id": product.product_variant_id.id,
                "csrf_token": csrf_token,
            },
        )
        csrf_token = self.csrf_token(
            self.url_open("/shop/checkout", timeout=self.timeout).text
        )
        self.post("/shop/confirm_order", data={"csrf_token": csrf_token})
