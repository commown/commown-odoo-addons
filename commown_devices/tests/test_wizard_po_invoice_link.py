import json

from odoo.exceptions import UserError

from .common import LinkWizardTC


class POInvoiceLinkWizardTC(LinkWizardTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        supplier_account = cls.env["account.account"].create(
            {
                "code": "CUST.ACC",
                "name": "customer account",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        base_inv_line = {"price_unit": 10.0, "account_id": supplier_account.id}
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.supplier.id,
                "line_ids": [
                    (0, 0, dict(base_inv_line, product_id=p.id, name=p.name))
                    for p in [cls.fp, cls.pc1, cls.pc2]
                ],
            }
        )

    def create_wizard(self):
        return (
            self.env["po.invoice.link.wizard"]
            .with_context(active_ids=[self.po.id], default_po_id=self.po.id)
            .create({})
        )

    def test_link_line_creation(self):
        wizard = self.create_wizard()
        self.assertEqual(len(wizard.link_line_ids), 3)
        self.assertEqual(wizard.link_line_ids.mapped("po_line_id"), self.po.order_line)

    def test_invoice_domain(self):
        wizard = self.create_wizard()
        base_domain = [("move_type", "=", "in_invoice")]
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

        # Perform a search with the generated domain, to insure it's valid.
        self.env["account.move"].search(invoice_domain)

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

        # Perform a search with the generated domain, to insure it's valid.
        self.env["account.move"].search(invoice_domain)

    def test_invoice_line_domain(self):
        wizard = self.create_wizard()
        lines_domain = set(wizard.mapped("link_line_ids.invoice_line_id_domain"))
        self.assertEqual(
            lines_domain,
            {'[["move_id", "=", false]]'},
        )

        # Perform a search with the generated domain, to insure it's valid.
        inv_lines = self.env["account.move.line"].search(json.loads(lines_domain.pop()))
        self.assertFalse(inv_lines)

        wizard.invoice_id = self.invoice.id
        wizard.link_line_ids._compute_invoice_line_id_domain()
        lines_domain = set(wizard.mapped("link_line_ids.invoice_line_id_domain"))
        self.assertEqual(
            lines_domain,
            {'[["move_id", "=", %s]]' % self.invoice.id},
        )

        # Perform a search with the generated domain, to insure it's valid.
        inv_lines = self.env["account.move.line"].search(json.loads(lines_domain.pop()))
        self.assertEqual(inv_lines, wizard.invoice_id.line_ids)

    def test_action_assign_invoice(self):
        self.assertFalse(self.po.order_line.mapped("invoice_lines"))
        wizard = (
            self.env["po.invoice.link.wizard"]
            .with_context(active_ids=[self.po.id], default_po_id=self.po.id)
            .create({})
        )
        for i in range(len(self.po.order_line)):
            wizard.link_line_ids[i].invoice_line_id = self.invoice.line_ids[i]
        wizard.action_assign_invoice()
        self.assertEqual(
            self.po.order_line.mapped("invoice_lines"),
            self.invoice.line_ids,
        )
        self.assertEqual(self.invoice.invoice_origin, self.po.name)
        self.assertEqual(
            set(self.invoice.line_ids.mapped("name")),
            {"%s: %s" % (self.po.name, p.name) for p in [self.fp, self.pc1, self.pc2]},
        )

        # If no link lines are present in the wizard (ie. all lines are already fused),
        # the wizard should raise an exception
        wizard = (
            self.env["po.invoice.link.wizard"]
            .with_context(active_ids=[self.po.id], default_po_id=self.po.id)
            .create({})
        )
        self.assertFalse(wizard.link_line_ids)

        with self.assertRaises(UserError) as exc:
            wizard.action_assign_invoice()
        self.assertIn("link is required", exc.exception.args[0])
