from odoo.tests.common import SavepointCase


class AccountInvoiceLineTC(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(AccountInvoiceLineTC, cls).setUpClass()

        def account(user_type_ref, group, code):
            ref = cls.env.ref
            return cls.env["account.account"].create(
                {
                    "name": "Test %s" % group,
                    "code": "01010%d" % code,
                    "user_type_id": ref("account.%s" % user_type_ref).id,
                    "internal_type": "other",
                    "internal_group": group,
                }
            )

        # Create accounts so that we do not depend on which l10n module is installed:
        cls.sales_account = account("data_account_type_expenses", "expense", 1)
        cls.rental_account = account("data_account_type_current_assets", "asset", 2)

        cls.product = cls.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
                "property_account_expense_id": cls.sales_account.id,
                "property_rental_account_expense_id": cls.rental_account.id,
            }
        )

        # Otherwise the product expense account is not the one on purchase for sale
        # invoices:
        cls.env.ref("base.main_company").anglo_saxon_accounting = False

    def purchase(self, picking_type_ref):
        oline_attrs = {
            "name": self.product.name,
            "date_planned": "2050-01-01",
            "product_id": self.product.product_variant_id.id,
            "product_uom": self.product.uom_id.id,
            "product_qty": 1,
            "price_unit": 1,
        }
        return self.env["purchase.order"].create(
            {
                "partner_id": self.env.ref("base.res_partner_1").id,
                "picking_type_id": self.env.ref(picking_type_ref).id,
                "order_line": [(0, 0, oline_attrs)],
            }
        )

    def invoice_account(self, po):
        invoice = self.env["account.invoice"].create(
            {
                "type": "in_invoice",
                "company_id": self.env.ref("base.main_company").id,
                "currency_id": self.env.ref("base.EUR").id,
                "partner_id": po.partner_id.id,
                "purchase_id": po.id,
            }
        )
        invoice.purchase_order_change()
        return invoice.invoice_line_ids.mapped("account_id")

    def test_purchase_account_rental_product(self):
        po = self.purchase("commown_devices.stock_picking_type_in_rental")
        self.assertEqual(self.invoice_account(po), self.rental_account)

    def test_purchase_account_rental_category(self):
        acc = self.product.property_rental_account_expense_id
        self.product.property_rental_account_expense_id = False
        self.product.categ_id = self.env["product.category"].create(
            {"property_rental_account_expense_categ_id": acc.id, "name": "tc"}
        )

        po = self.purchase("commown_devices.stock_picking_type_in_rental")
        self.assertEqual(self.invoice_account(po), self.rental_account)

    def test_purchase_account_sales(self):
        po = self.purchase("stock.picking_type_internal")
        self.assertEqual(self.invoice_account(po), self.sales_account)
