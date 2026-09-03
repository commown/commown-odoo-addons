from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from .common import NetinstallMixin


@tagged("-at_install", "post_install")
class NetinstallerProductTC(TransactionCase, NetinstallMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pt = cls.env.ref("product_rental.prod_pc")
        cls.pt.netinstaller_feature_value_ids |= cls.lref("nv")
        cls.pt.netinstaller_feature_value_ids |= cls.lref("ram-8")

    def test_cumulated_feature_values_no_attr_overload(self):
        pp = self.pt.product_variant_ids[0]
        self.assertEqual(
            pp.netinstaller_feature_typed_values(),
            {"RAM": 8, "MODEL": "NV4XMB,ME,MZ"},
        )

    def test_cumulated_feature_values_with_attr_overload(self):
        self.env["product.template.attribute.line"].create(
            {
                "attribute_id": self.lref("memory").id,
                "product_tmpl_id": self.pt.id,
                "value_ids": [
                    Command.link(self.lref("memory-8go").id),
                    Command.link(self.lref("memory-16go").id),
                ],
            },
        )

        pp = self.pt.product_variant_ids.filtered(lambda v: "16" in v.display_name)[0]
        self.assertEqual(
            pp.netinstaller_feature_typed_values(),
            {"RAM": 16, "MODEL": "NV4XMB,ME,MZ"},
        )
