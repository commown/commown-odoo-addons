from lxml import html

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class CrmLeadTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        self.partner1 = self.env["res.partner"].create({"name": "Tutu"})
        self.partner2 = self.env["res.partner"].create({"name": "Toto"})

        self.company = self.env["res.partner"].create(
            {"name": "Big Corp", "is_company": True}
        )

        self.product1 = self._create_rental_product(name="Fairphone Premium")
        self.product2 = self._create_rental_product(name="Crosscall")

        self.so1 = self.create_so(self.partner1, self.product1)
        self.so2 = self.create_so(self.partner2, self.product2, qty=2)

        self.lead = self.create_lead_from_so(self.so1)

    def create_so(self, partner, product, qty=1):
        so_line = self._oline(product, product_uom_qty=qty)
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [so_line],
            }
        )

    def create_lead_from_so(self, so):
        return self.env["crm.lead"].create(
            {
                "name": "Test Lead",
                "partner_id": so.partner_id.id,
                "so_line_id": so.order_line.id,
            }
        )

    def test_compute_orders_descr_no_partner(self):
        self.lead.partner_id = False
        self.lead._compute_orders_descr()
        self.assertFalse(self.lead.orders_description)

    def test_compute_orders_descr_complete(self):
        def get_html():
            self.lead._compute_orders_descr()
            return html.fromstring(self.lead.orders_description)

        # If so is not confirmed, order descriptions is empty
        self.lead._compute_orders_descr()
        self.assertFalse(self.lead.orders_description)

        # Otherwise and if partner has no company orders, check its order list:
        self.so1.action_confirm()

        actual = get_html()
        self.assertEqual(actual.xpath("//h3/text()"), [self.so1.name])
        self.assertEqual(actual.xpath("//li/text()"), ["Fairphone Premium"])

        # ... and if it has a company, the description has a product summary too:
        self.partner1.parent_id = self.company
        self.partner2.parent_id = self.company
        self.so2.action_confirm()

        actual = get_html()

        order_els = actual.xpath("//*[hasclass('partner-order')]")
        self.assertEqual(len(order_els), 2)
        self.assertEqual(order_els[0].xpath(".//h3/text()"), [self.so2.name])
        self.assertEqual(order_els[0].xpath(".//li/text()"), ["Crosscall"])
        self.assertEqual(order_els[1].xpath(".//h3/text()"), [self.so1.name])
        self.assertEqual(order_els[1].xpath(".//li/text()"), ["Fairphone Premium"])

        sum_els = actual.xpath("//*[hasclass('product-summary')]")
        self.assertEqual(len(sum_els), 1)
        sum_el = sum_els[0]

        self.assertEqual(
            sum_el.xpath(".//h3/text()"),
            ["Summary for company: Big Corp"],
        )

        def text(el):
            return " ".join(t.strip() for t in el.itertext() if t.strip())

        self.assertEqual(len(sum_el.xpath(".//li")), 2)
        self.assertEqual(text(sum_el.xpath(".//li")[0]), "2 Crosscall")
        self.assertEqual(text(sum_el.xpath(".//li")[1]), "1 Fairphone Premium")

        # Also test with a holding
        holding = self.env["res.partner"].create(
            {"name": "Holding", "is_company": True}
        )
        self.company.parent_id = holding.id
        partner3 = self.env["res.partner"].create(
            {"name": "Titi", "parent_id": holding.id}
        )
        so3 = self.create_so(partner3, self.product2)
        so3.action_confirm()

        actual = get_html()
        sum_els = actual.xpath("//*[hasclass('product-summary')]")
        self.assertEqual(len(sum_els), 2)
        sum_el = sum_els[1]

        self.assertEqual(sum_el.xpath(".//h3/text()"), ["Summary for company: Holding"])

        self.assertEqual(len(sum_el.xpath(".//li")), 2)
        self.assertEqual(text(sum_el.xpath(".//li")[0]), "3 Crosscall")
        self.assertEqual(text(sum_el.xpath(".//li")[1]), "1 Fairphone Premium")
