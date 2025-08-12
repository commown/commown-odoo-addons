from odoo.tests import tagged

from odoo.addons.account_invoice_merge_auto_pay.tests.test_account_move import (
    AccountMoveTC,
)


@tagged("-at_install", "post_install")
class AccountInvoiceTC(AccountMoveTC):
    def test_user_id_ignored_in_invoice_merge(self):
        """
        When merging invoices, the (invoice_)user_id should not
        be used as a key to sync invoices, even if they differ.
        """
        demo_user_1 = self.env.ref("base.user_demo")
        demo_user_2 = self.env.ref("base.demo_user0")
        self.assertNotIn(self.env.user, (demo_user_1 | demo_user_2))

        inv_1 = self.create_invoice(self.partner_a, "2019-05-09", 60)
        inv_1.invoice_user_id = demo_user_1
        inv_2 = self.create_invoice(self.partner_a, "2019-05-10", 60)
        inv_2.invoice_user_id = demo_user_2

        # Testing the method overload
        self.assertNotIn("user_id", inv_1._get_invoice_key_cols())

        # Merge the invoices
        # Their (invoice_)user_id fields shouldn't interfere with the merge or be used.
        _, merge_infos = self.env["account.move"]._cron_invoice_merge("2019-05-16")
        new_inv = self.env["account.move"].browse(list(merge_infos.keys())[0]).exists()

        self.assertEqual(new_inv.user_id, self.env.user)

    def test_merge_auto_pay_sends_email(self):
        p_inv = self.partner_a.copy(
            {
                "type": "invoice",
                "parent_id": self.partner_a.id,
                "email": "test@test.coop",
            }
        )
        self.create_invoice(p_inv, "2019-05-09", 60)
        self.create_invoice(p_inv, "2019-05-10", 60)

        new_inv = self._merge_and_pay()

        mail = self.env["mail.mail"].search(
            [
                ("model", "=", new_inv._name),
                ("res_id", "=", new_inv.id),
                ("attachment_ids.res_name", "=", new_inv.display_name),
                ("attachment_ids.mimetype", "=", "application/pdf"),
            ]
        )
        self.assertTrue(mail)
