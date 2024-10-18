from .common import WebsiteBaseTC


def _clean_text(node):
    return " ".join(t.strip() for t in node.itertext() if t.strip())


class WebsiteTC(WebsiteBaseTC):
    def setUp(self):
        super().setUp()
        self.so = self.create_sale_order(self.partner)
        self.so.action_confirm()
        self.contracts = self.env["contract.contract"].search(
            [
                ("name", "ilike", "%" + self.so.name + "%"),
            ]
        )

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
                "serenity level services (deposit)",
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
