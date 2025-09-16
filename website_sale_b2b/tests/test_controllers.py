from re import sub

from lxml.html import fromstring

import odoo
from odoo.tests.common import HttpCase, tagged

from odoo.addons.product_rental.tests.common import RentalSaleOrderMixin


@tagged("-at_install", "post_install")
class WebsiteSaleB2BControllersTC(RentalSaleOrderMixin, HttpCase):
    timeout = 3000

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.so = cls.create_sale_order(cls.env.ref("base.res_partner_address_1"))

        cls.fp_premium = cls._product_by_name("Fairphone Premium")
        cls.fp2 = cls._product_by_name("FP2")
        cat = cls.env["product.public.category"]
        cls.cat_fp = cat.create({"name": "FP"})
        cls.cat_fp_premium = cat.create(
            {"name": "FP Premium", "parent_id": cls.cat_fp.id}
        )
        cls.fp2.public_categ_ids |= cls.cat_fp
        cls.fp_premium.public_categ_ids |= cls.cat_fp_premium

        cls.so.action_confirm()

        cls.contracts = cls.env["contract.contract"].of_sale(cls.so)
        cls.contracts.mapped("contract_line_ids").update({"date_start": "2022-01-01"})

        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "test", "account_for_rented_quantity": "product-category"}
        )
        cls.pricelist.account_for_rented_quantity_category_ids |= cls.cat_fp

        cls.pricelist_item = cls.env["product.pricelist.item"].create(
            {
                "pricelist_id": cls.pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": cls.fp_premium.id,
                "compute_price": "percentage",
                "percent_price": 20.0,
                "min_quantity": 10,
            }
        )

    @classmethod
    def _product_by_name(cls, name):
        return cls.env["product.template"].search([("name", "=", name)]).ensure_one()

    def get_rental_price(self, html):
        prices = html.xpath(
            "//*[hasclass('oe_recurrent_payment_amount')]"
            "//*[hasclass('oe_currency_value')]/text()"
        )
        self.assertEqual(len(prices), 1)
        return float(prices[0])

    def get_add_qty(self, html):
        return float(html.xpath("//input[@name='add_qty']/@value")[0])

    def _clean_tag_text(self, html_tag):
        return " ".join(sub(r"(\s)+", " ", s.strip()) for s in html_tag.itertext())

    def test_rental_price(self):
        # Publish the product on the web...
        self.fp_premium.website_published = True

        # (For integration testing, the product must appear in the categ_de public category
        # due to the `commown module`)
        categ_de = self.env.ref("commown.categ_de", raise_if_not_found=False)
        if categ_de:  # pragma: no cover
            self.fp_premium.public_categ_ids |= categ_de

        # ... and simulate we are on the B2B website
        self.env["ir.model.data"].search(
            [("module", "=", "website_b2b"), ("name", "=", "b2b_website")]
        ).res_id = 1

        # Fetch the FP premium page as user of the company who already rents devices:
        user = self.env.ref("base.demo_user0")
        user.partner_id.commercial_partner_id = self.so.partner_id.commercial_partner_id

        session = self.authenticate(user.login, "portal")
        session["website_sale_current_pl"] = self.pricelist.id
        odoo.http.root.session_store.save(session)

        # Check the result...
        resp = self.url_open(self.fp_premium.website_url, timeout=self.timeout)
        page = fromstring(resp.text)
        # ... rental price accounts for the pricelist reduction,
        self.assertEqual(self.get_rental_price(page), 24.0)
        # ... the selected quantity accounts for the pricelist item minimum quantity
        self.assertEqual(self.get_add_qty(page), 10.0)
        # ... and a text explains why this price
        self.assertEqual(
            self._clean_tag_text(page.xpath("//div[@id='add_to_cart_wrap']/div")[0]),
            "This reduced price takes into account the 2 devices of the FP category you already have.",
        )
