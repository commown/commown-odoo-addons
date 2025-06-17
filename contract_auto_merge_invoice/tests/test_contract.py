from odoo.addons.contract.tests.test_contract import TestContractBase


class ContractTC(TestContractBase):
    def test_auto_merge_invoice(self):
        partner = self.contract.partner_id

        invoice = self.contract.recurring_create_invoice()
        self.assertTrue(invoice.auto_merge)

        self.assertEqual(partner.invoice_merge_recurring_rule_type, "monthly")
        self.assertEqual(partner.invoice_merge_recurring_interval, 1)
        self.assertEqual(partner.invoice_merge_next_date, invoice.date_invoice)
