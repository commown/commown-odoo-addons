from odoo import Command

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC

from .common import NetinstallMixin


class NetinstallerContractTC(RentalSaleOrderTC, NetinstallMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.res_partner_address_1")

        contract_tmpl = cls._create_rental_contract_tmpl(
            1,
            contract_line_ids=[cls._contract_line(1, "1 month ##PRODUCT##")],
        )
        cls.service_tmpl = cls.env.ref("product_rental.prod_pc")
        cls.service_tmpl.write(
            {
                "property_contract_template_id": contract_tmpl,
                "netinstaller_feature_value_ids": [
                    Command.set((cls.lref("nv") | cls.lref("ram-8")).ids),
                ],
            }
        )
        cls.service_product = cls.service_tmpl.product_variant_ids[0]

        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "partner_invoice_id": cls.partner.id,
                "partner_shipping_id": cls.partner.id,
                "order_line": [cls._oline(cls.service_product)],
            }
        )
        cls.so.action_confirm()
        cls.contract = cls.env["contract.contract"].of_sale(cls.so)

    def test_contract_netinstaller_specs(self):
        self.assertEqual(
            self.contract.netinstaller_specs(),
            {"RAM": 8, "MODEL": "NV4XMB,ME,MZ"},
        )
