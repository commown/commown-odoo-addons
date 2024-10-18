import lxml.html
from mock import patch

from odoo import api
from odoo.tests.common import SavepointCase

from odoo.addons.queue_job.tests.common import trap_jobs
from odoo.addons.website.models.website import Website  # see mock
from odoo.addons.website.tools import MockRequest

from ..models.contract import NO_DATE


class MockedEmptySessionMixin(object):
    def setUp(self):
        request_patcher = patch(
            "odoo.addons.website_sale_affiliate"
            ".models.sale_affiliate_request.request"
        )
        self.request_mock = request_patcher.start()
        self.request_mock.configure_mock(session={})
        self.fake_session = self.request_mock.session
        self.addCleanup(request_patcher.stop)

        super(MockedEmptySessionMixin, self).setUp()


class RentalSaleOrderMixin:
    def get_default_tax(self, amount=20.0):
        return self.env["account.tax"].create(
            {
                "amount": amount,
                "amount_type": "percent",
                "price_include": True,  # french style
                "name": "Default test tax",
                "type_tax_use": "sale",
            }
        )

    def create_sale_order(self, partner=None, tax=None, env=None):
        """Given tax (defaults to company's default) is used for contract
        products.
        """
        env = env or self.env
        if partner is None:
            partner = env.ref("base.res_partner_3")
        if tax is None:
            tax = self.get_default_tax()
        # Main rental products (with a rental contract template)
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                self._contract_line(
                    1, "1 month Fairphone premium", tax, specific_price=25.0
                ),
                self._contract_line(2, "1 month ##ACCESSORY##", tax),
            ],
        )
        product1 = self._create_rental_product(
            name="Fairphone Premium",
            list_price=60.0,
            rental_price=30.0,
            property_contract_template_id=contract_tmpl1.id,
        )
        oline_p1 = self._oline(product1)

        contract_tmpl2 = self._create_rental_contract_tmpl(
            2,
            contract_line_ids=[
                self._contract_line(
                    1, "1 month of ##PRODUCT##", tax, specific_price=0.0
                ),
                self._contract_line(2, "1 month of ##ACCESSORY##", tax),
            ],
        )
        product2 = self._create_rental_product(
            name="PC",
            list_price=130.0,
            rental_price=65.0,
            property_contract_template_id=contract_tmpl2.id,
        )
        oline_p2 = self._oline(product2, product_uom_qty=2, price_unit=120)

        contract_tmpl3 = self._create_rental_contract_tmpl(
            3,
            contract_line_ids=[
                self._contract_line(
                    1, "1 month of ##PRODUCT##", tax, specific_price=0.0
                ),
                self._contract_line(2, "1 month of ##ACCESSORY##", tax),
            ],
        )
        product3 = self._create_rental_product(
            name="GS Headset",
            list_price=1.0,
            rental_price=10.0,
            property_contract_template_id=contract_tmpl3.id,
            is_deposit=False,
        )
        oline_p3 = self._oline(product3, product_uom_qty=1, price_unit=1.0)

        contract_tmpl4 = self._create_rental_contract_tmpl(
            4,
            contract_line_ids=[
                self._contract_line(
                    1,
                    "1 month of ##PRODUCT##",
                    tax,
                    specific_price=0.0,
                ),
                self._contract_line(
                    2,
                    "1 month of ##ACCESSORY##",
                    tax,
                    specific_price=0.0,
                ),
            ],
        )
        product4 = self._create_rental_product(
            name="FP2",
            list_price=40.0,
            rental_price=20.0,
            property_contract_template_id=contract_tmpl4.id,
        )
        oline_p4 = self._oline(product4, product_uom_qty=1)

        # Accessory products
        a1 = self._create_rental_product(
            name="headset",
            list_price=3.0,
            rental_price=1.5,
            property_contract_template_id=False,
        )
        oline_a1 = self._oline(a1)

        a2 = self._create_rental_product(
            name="screen",
            list_price=30.0,
            rental_price=15.0,
            property_contract_template_id=False,
        )
        oline_a2 = self._oline(a2, product_uom_qty=4)

        a3 = self._create_rental_product(
            name="keyboard",
            list_price=12.0,
            rental_price=6.0,
            property_contract_template_id=False,
        )
        oline_a3 = self._oline(a3, discount=10)

        a4 = self._create_rental_product(
            name="keyboard deluxe",
            list_price=15.0,
            rental_price=7.5,
            property_contract_template_id=False,
        )
        oline_a4 = self._oline(a4)

        product1.accessory_product_ids |= a1
        product2.accessory_product_ids |= a2 + a3 + a4

        # Optional products
        o1 = self._create_rental_product(
            name="serenity level services",
            list_price=3.0,
            rental_price=6.0,
            property_contract_template_id=False,
        )
        oline_o1 = self._oline(o1)
        product3.optional_product_ids |= o1.product_tmpl_id

        return env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [
                    oline_p1,
                    oline_p2,
                    oline_p3,
                    oline_p4,
                    oline_a1,
                    oline_a2,
                    oline_a3,
                    oline_a4,
                    oline_o1,
                ],
            }
        )

    def generate_contract_invoices(self, partner=None, tax=None):
        so = self.create_sale_order(partner, tax)
        so.action_confirm()
        contracts = self.env["contract.contract"].of_sale(so)
        lines = contracts.mapped("contract_line_ids")
        self.assertEqual(set(lines.mapped("date_start")), {NO_DATE})
        # Do not use _recurring_create_invoice return value here as
        # contract_queue_job (installed in the CI) returns an empty invoice set
        # (see https://github.com/OCA/contract/blob/12.0/contract_queue_job
        #  /models/contract_contract.py#L21)
        with trap_jobs() as trap:
            contracts._recurring_create_invoice()
        trap.perform_enqueued_jobs()
        invoices = self.env["account.invoice"].search(
            [
                ("invoice_line_ids.contract_line_id.contract_id", "in", contracts.ids),
            ]
        )
        return invoices

    def _create_rental_product(self, name, **kwargs):
        kwargs["name"] = name
        kwargs.setdefault("is_rental", True)
        kwargs.setdefault("type", "service")
        kwargs.setdefault("taxes_id", False)
        kwargs["is_contract"] = bool(kwargs.get("property_contract_template_id"))
        result = self.env["product.product"].create(kwargs)
        # Otherwise is_contract may be wrong (in one of commown_devices tests):
        result.env.cache.invalidate()
        return result

    def _create_rental_contract_tmpl(self, num, **kwargs):
        kwargs.setdefault("name", "Test Contract Template %d" % num)
        kwargs.setdefault("commitment_period_number", 12)
        kwargs.setdefault("commitment_period_type", "monthly")
        return self.env["contract.template"].create(kwargs)

    def _oline(self, product, **kwargs):
        kwargs["product_id"] = product.id
        kwargs["product_uom"] = product.uom_id.id
        kwargs.setdefault("name", product.name)
        kwargs.setdefault("product_uom_qty", 1)
        kwargs.setdefault("price_unit", product.list_price)
        return (0, 0, kwargs)

    def _contract_line(self, num, name, product_tax=None, **kwargs):
        if "product_id" not in kwargs:
            product = self.env["product.product"].create(
                {"name": "Contract product %d" % num, "type": "service"}
            )
            if product_tax is not None:
                product.taxes_id = False
                product.taxes_id |= product_tax
            kwargs["product_id"] = product.id
            kwargs["uom_id"] = product.uom_id.id
        kwargs["name"] = name
        kwargs.setdefault("specific_price", 0.0)
        kwargs.setdefault("quantity", 1)
        kwargs.setdefault("recurring_rule_type", "monthly")
        kwargs.setdefault("recurring_interval", 1)
        return (0, 0, kwargs)


class RentalSaleOrderTC(MockedEmptySessionMixin, RentalSaleOrderMixin, SavepointCase):
    pass


class WebsiteBaseTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        # Use a portal user to avoid language selector rendering
        # (other page is editable and the selector is more complex)
        env = api.Environment(self.env.cr, self.partner.user_ids[0].id, {})
        self.website = self.env.ref("website.default_website").with_env(env)

    def render_view(self, ref, **render_kwargs):
        view = self.env.ref(ref)
        with patch.object(Website, "get_alternate_languages", return_value=()):
            with MockRequest(self.env, website=self.website) as request:
                request.httprequest.args = []
                request.httprequest.query_string = ""
                request.endpoint_arguments = {}
                html = view.render(render_kwargs)
        return lxml.html.fromstring(html)
