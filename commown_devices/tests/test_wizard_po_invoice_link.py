from datetime import date

from .common import DeviceAsAServiceTC


class POInvoiceLinkWizardTC(DeviceAsAServiceTC):
    def setUp(self):
        super().setUp()
        supplier = self.env.ref("base.res_partner_3")
        self.fp = self.env.ref("product_rental.prod_fp")
        self.pc1 = self.env.ref("product_rental.prod_pc_i5")
        self.pc2 = self.env.ref("product_rental.prod_pc_i7")
        oline1 = self._oline(self.fp, product_qty=3, date_planned=date(2021, 1, 1))
        oline2 = self._oline(self.pc1, product_qty=5, date_planned=date(2021, 1, 1))
        oline3 = self._oline(self.pc2, product_qty=8, date_planned=date(2021, 1, 1))
        self.po = self.env["purchase.order"].create(
            {
                "partner_id": supplier.id,
                "order_line": [oline1, oline2, oline3],
            }
        )

        supplier_account = self.env["account.account"].create(
            {
                "code": "cust_acc",
                "name": "customer account",
                "user_type_id": self.env.ref("account.data_account_type_payable").id,
                "reconcile": True,
            }
        )
        base_inv_line = {"price_unit": 10.0, "account_id": supplier_account.id}
        self.invoice = self.env["account.invoice"].create(
            {
                "type": "in_invoice",
                "partner_id": supplier.id,
                "account_id": supplier_account.id,
                "invoice_line_ids": [
                    (0, 0, dict(base_inv_line, product_id=p.id, name=p.name))
                    for p in [self.fp, self.pc1, self.pc2]
                ],
            }
        )

    def prepare_wizard(self, related_entity, relation_field, user_choices=None):
        wizard_name = "po.invoice.link.wizard"
        return self.prepare_ui(
            wizard_name, related_entity, relation_field, user_choices=user_choices
        )

    def create_wizard(self):
        return (
            self.env["po.invoice.link.wizard"]
            .with_context({"active_ids": [self.po.id], "default_po_id": self.po.id})
            .create({})
        )

    def test_link_line_creation(self):
        wizard = self.create_wizard()
        self.assertEqual(len(wizard.link_line_ids), 3)
        self.assertEqual(wizard.link_line_ids.mapped("po_line_id"), self.po.order_line)

    def test_invoice_domain(self):
        wizard = self.create_wizard()
        base_domain = [("type", "=", "in_invoice")]
        # Test prerequisite
        self.assertTrue(wizard.po_id.partner_id.commercial_partner_id)

        invoice_domain = wizard._compute_invoice_domain()["domain"]["invoice_id"]
        self.assertEqual(
            set(invoice_domain),
            set(
                [
                    (
                        "partner_id.commercial_partner_id",
                        "=",
                        self.po.partner_id.commercial_partner_id.id,
                    )
                ]
                + base_domain
            ),
        )

        wizard.po_id.partner_id.commercial_partner_id = False
        invoice_domain = wizard._compute_invoice_domain()["domain"]["invoice_id"]
        self.assertEqual(
            set(invoice_domain),
            set(
                [
                    (
                        "partner_id",
                        "=",
                        self.po.partner_id.id,
                    )
                ]
                + base_domain
            ),
        )

    def test_invoice_line_domain(self):
        wizard = self.create_wizard()
        self.assertEqual(
            set(wizard.mapped("link_line_ids.invoice_line_id_domain")),
            {'[["invoice_id", "=", false]]'},
        )
        wizard.invoice_id = self.invoice.id
        wizard.link_line_ids._compute_invoice_line_id_domain()
        self.assertEqual(
            set(wizard.mapped("link_line_ids.invoice_line_id_domain")),
            {'[["invoice_id", "=", %s]]' % self.invoice.id},
        )

    def test_action_assign_invoice(self):
        self.assertFalse(self.po.order_line.mapped("invoice_lines"))
        wizard = (
            self.env["po.invoice.link.wizard"]
            .with_context({"active_ids": [self.po.id], "default_po_id": self.po.id})
            .create({})
        )
        for i in range(len(self.po.order_line)):
            wizard.link_line_ids[i].invoice_line_id = self.invoice.invoice_line_ids[i]
        wizard.action_assign_invoice()
        self.assertEqual(
            self.po.order_line.mapped("invoice_lines"),
            self.invoice.invoice_line_ids,
        )
        self.assertEqual(self.invoice.origin, self.po.name)
        self.assertEqual(
            set(self.invoice.invoice_line_ids.mapped("name")),
            {"%s: %s" % (self.po.name, p.name) for p in [self.fp, self.pc1, self.pc2]},
        )
