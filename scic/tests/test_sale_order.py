from odoo.fields import Command
from odoo.tests.common import TransactionCase


def _get_line_by_equity_type(so, equity_type):
    return so.order_line.filtered(
        lambda line: line.product_id.product_tmpl_id.equity_type == equity_type
    )


class SaleOrderTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        crowd_equity_template = cls._create_product_template("crowd")
        invest_equity_template = cls._create_product_template("invest")

        cls.crowd_product = crowd_equity_template.product_variant_id
        cls.invest_product = invest_equity_template.product_variant_id

    @classmethod
    def _create_product_template(cls, equity_type):
        return cls.env["product.template"].create(
            {
                "name": "Test %s equity" % equity_type,
                "is_equity": True,
                "equity_type": equity_type,
            }
        )

    def _create_order(self, products):
        user_demo = self.env.ref("base.user_demo")
        return self.env["sale.order"].create(
            {
                "partner_id": user_demo.partner_id.id,
                "state": "draft",
                "order_line": [
                    Command.create(
                        {
                            "product_id": pt.id,
                        }
                    )
                    for pt in products
                ],
            }
        )

    def test_cart_update(self):
        so = self._create_order([self.crowd_product, self.invest_product])
        crowd_line = _get_line_by_equity_type(so, "crowd")
        invest_line = _get_line_by_equity_type(so, "invest")

        expected_message = (
            "Forced quantity update of line %(l)s (product %(p)s) from %(old_qty)s"
            " to %(new_qty)s"
            % {
                "l": crowd_line.id,
                "p": self.crowd_product.name,
                "old_qty": 34.0,
                "new_qty": 1,
            }
        )

        chan = "odoo.addons.scic.models.sale_order"
        with self.assertLogs(chan, level="DEBUG") as cm:
            so._cart_update(self.crowd_product.id, crowd_line.id, set_qty=34)
            so._cart_update(self.invest_product.id, invest_line.id, set_qty=34)

        self.assertEqual("DEBUG:%s:%s" % (chan, expected_message), cm.output[0])

        self.assertEqual(invest_line.product_uom_qty, 34)
        self.assertEqual(crowd_line.product_uom_qty, 1)

    def test_has_crowd_equity(self):
        so_crowd = self._create_order([self.crowd_product])
        so_no_crowd = self._create_order([self.invest_product])

        self.assertTrue(so_crowd.has_crowd_equity())
        self.assertFalse(so_no_crowd.has_crowd_equity())

    def test_has_investment(self):
        so_invest = self._create_order([self.invest_product])
        so_no_invest = self._create_order([self.crowd_product])

        self.assertTrue(so_invest.has_investment())
        self.assertFalse(so_no_invest.has_investment())
