from odoo import Command
from odoo.tests import TransactionCase


class PropertyAccountsAccountMoveTC(TransactionCase):
    def test_automatic_payable_account_creation(self):
        "A payable account should be created to any partner assigned to a Vendor Bill"

        # Setup
        Partner = self.env["res.partner"]
        Move = self.env["account.move"]

        company_1, company_2 = Partner.create(
            [
                {"name": "Company 1", "is_company": True},
                {"name": "Company 2", "is_company": True},
            ]
        )
        empl_1, empl_2 = Partner.create(
            [
                {"name": "Employee 1", "parent_id": company_1.id},
                {"name": "Employee 2", "parent_id": company_2.id},
            ]
        )

        ref_account = self.env["ir.property"]._get(
            "property_account_payable_id", "res.partner"
        )

        product = self.env.ref("product.product_product_1_product_template")

        # Use case 1: On account.move create
        # (Simulate account.move creation through shell)
        cmp_1_partners = company_1 | empl_1
        self.assertEqual(ref_account, cmp_1_partners.property_account_payable_id)

        mv_1 = Move.create(
            {
                "move_type": "in_invoice",
                "line_ids": [Command.create({"product_id": product.id})],
                "partner_id": company_1.id,
            }
        )

        cmp_1_payable_account = company_1.property_account_payable_id
        self.assertNotEqual(cmp_1_payable_account, ref_account)
        self.assertEqual(
            cmp_1_payable_account, cmp_1_partners.property_account_payable_id
        )

        mv_1_term_line = mv_1.line_ids.filtered(
            lambda ml: ml.display_type == "payment_term"
        )
        self.assertEqual(cmp_1_payable_account, mv_1_term_line.account_id)

        # Use case 2: On account.move write
        # (Simulate account.move creation through Vendors bill action window)
        mv_2 = Move.with_context(default_move_type="in_invoice").create(
            {"line_ids": [Command.create({"product_id": product.id})]}
        )
        mv_2_term_line = mv_2.line_ids.filtered(
            lambda ml: ml.display_type == "payment_term"
        )
        self.assertIn(ref_account, mv_2_term_line.account_id)

        cmp_2_partners = company_2 | empl_2
        self.assertEqual(ref_account, cmp_2_partners.property_account_payable_id)

        mv_2.partner_id = empl_2

        cmp_2_payable_account = empl_2.property_account_payable_id
        self.assertNotEqual(cmp_2_payable_account, ref_account)
        self.assertEqual(
            cmp_2_payable_account, cmp_2_partners.property_account_payable_id
        )

        self.assertEqual(cmp_2_payable_account, mv_2_term_line.account_id)
