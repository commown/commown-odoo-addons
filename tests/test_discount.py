from odoo.addons.contract.tests.test_contract import TestContractBase


class DiscountLineTC(TestContractBase):

    def test_no_issue_condition(self):
        self.env['contract.discount.line'].create({
            "name": u"Fix discount",
            "amount_type": u"fix",
            "amount_value": 5.,
            "contract_line_id": self.acct_line.id,
            "condition": u"no_issue_to_date",
        })

        # Test without penalty
        self.assertFalse(self.contract.contractual_issue_ids)
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": u"task1",
            "penalty_exemption": True,
            "contractual_issue_date": self.contract.date_start,
        })

        inv1 = self.contract.recurring_create_invoice()
        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [5.])

        # Add a penalty
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": u"task2",
            "penalty_exemption": False,
            "contractual_issue_date": self.contract.date_start,
        })

        inv2 = self.contract.recurring_create_invoice()
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [0.])
