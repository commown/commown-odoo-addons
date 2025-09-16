from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class ResPartnerSimpleTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

    def test_create_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "supplier_rank": 1})

        expected = "401.F.%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)

    def test_create_supplier_no_ir_property(self):
        self.env["ir.property"]._get_property(
            "property_account_payable_id", "res.partner", False
        ).unlink()
        p1 = self.env["res.partner"].create({"name": "p1", "supplier_rank": 1})

        self.assertTrue(p1.property_account_payable_id)

    def test_update_to_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "supplier_rank": 0})

        expected = "401.F.%d" % p1.id
        self.assertNotEqual(p1.property_account_payable_id.code, expected)

        p1.supplier_rank = 1
        self.assertEqual(p1.property_account_payable_id.code, expected)

    def test_create_supplier_add_child(self):
        p1 = self.env["res.partner"].create(
            {"name": "p1", "supplier_rank": 1, "is_company": True}
        )
        p2 = self.env["res.partner"].create({"name": "p2", "parent_id": p1.id})

        expected = "401.F.%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)
        self.assertEqual(p2.property_account_payable_id.code, expected)

    def test_create_child_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "is_company": True})
        p2 = self.env["res.partner"].create({"name": "p2", "parent_id": p1.id})
        p3 = self.env["res.partner"].create({"name": "p3", "parent_id": p1.id})

        p3.supplier_rank = 1

        expected = "401.F.%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)
        self.assertEqual(p2.property_account_payable_id.code, expected)
        self.assertEqual(p3.property_account_payable_id.code, expected)

    def test_create_company_set_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test P", "customer_rank": 1, "company_name": "Test company"},
        )

        partner._create_receivable_account()
        recv_acc = partner.property_account_receivable_id
        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, recv_acc)
        self.assertEqual(recv_acc.name, "Test company")
        self.assertEqual(recv_acc.code, "411.C.%d" % company.id)

    def test_create_company_with_custom_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test P", "customer_rank": 1, "company_name": "Test company"},
        )

        partner._create_receivable_account()
        recv_acc = partner.property_account_receivable_id
        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, recv_acc)
        self.assertEqual(recv_acc.name, "Test company")
        self.assertEqual(recv_acc.code, "411.C.%d" % company.id)

    def test_create_company_without_custom_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test P", "customer_rank": 1, "company_name": "Test company"},
        )

        # Test prerequisite:
        ref_account = self.env["ir.property"]._get(
            "property_account_receivable_id",
            "res.partner",
        )
        ref_account.ensure_one()
        ref_account_old_code = ref_account.code

        self.assertEqual(partner.property_account_receivable_id, ref_account)

        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, ref_account)
        self.assertEqual(ref_account.code, ref_account_old_code)  # unchanged!
