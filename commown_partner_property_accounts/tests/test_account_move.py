from odoo import Command
from odoo.tests import Form, TransactionCase
from odoo.tools.safe_eval import safe_eval


class PropertyAccountsAccountMoveTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1, cls.partner_2 = cls.env["res.partner"].create(
            [
                {"name": "Partner 1"},
                {"name": "Partner 2"},
            ]
        )

        cls.ref_account = cls.env["ir.property"]._get(
            "property_account_payable_id", "res.partner"
        )

        cls.product = cls.env.ref("product.product_product_1")

    def assertPaymentTermAccount(self, move, expected_account):
        lines = move.line_ids.filtered(lambda ml: ml.display_type == "payment_term")
        self.assertEqual(set(lines.mapped("account_id")), {expected_account})

    def test_shell_automatic_payable_account_creation(self):
        "A payable account should be created to any partner assigned to a Vendor Bill"
        # Use case 1: On account.move create
        self.assertEqual(self.ref_account, self.partner_1.property_account_payable_id)

        mv = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "line_ids": [Command.create({"product_id": self.product.id})],
                "partner_id": self.partner_1.id,
            }
        )

        p1_payable_account = self.partner_1.property_account_payable_id
        self.assertNotEqual(p1_payable_account, self.ref_account)
        self.assertPaymentTermAccount(mv, p1_payable_account)

        # Use case 2: On account.move write

        mv.partner_id = self.partner_2

        p2_payable_account = self.partner_2.property_account_payable_id

        self.assertNotEqual(p2_payable_account, self.ref_account)
        self.assertPaymentTermAccount(mv, p2_payable_account)

    def test_ui_automatic_payable_account_creation(self):
        "From a form view, a payable account should be created for partners of Vendor Bills"

        # Setup - simulate Move creation/edit with Vendors Bill action context
        vendors_bills_action = self.env.ref("account.action_move_in_invoice_type")
        move_model = self.env["account.move"].with_context(
            **safe_eval(vendors_bills_action.context)
        )

        # Use case 1: On account.move create
        form_create = Form(move_model)

        form_create.partner_id = self.partner_1
        with form_create.invoice_line_ids.new() as line_form_create:
            line_form_create.product_id = self.product

        mv = form_create.save()

        p1_payable_account = self.partner_1.property_account_payable_id
        self.assertNotEqual(p1_payable_account, self.ref_account)
        self.assertPaymentTermAccount(mv, p1_payable_account)

        # Use case 2: On account.move write
        with Form(mv) as form_update:
            form_update.partner_id = self.partner_2

        p2_payable_account = self.partner_2.property_account_payable_id
        self.assertNotEqual(p2_payable_account, self.ref_account)
        self.assertPaymentTermAccount(mv, p2_payable_account)
