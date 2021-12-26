from odoo.addons.contract.tests.test_contract import TestContractBase

from .common import ContractSaleWithCouponTC


class DiscountLineTC(TestContractBase):

    def setUp(self):
        super(DiscountLineTC, self).setUp()
        self.contract.is_auto_pay = False

    def test_no_issue_condition(self):
        self.env['contract.discount.line'].create({
            "name": "Fix discount",
            "amount_type": "fix",
            "amount_value": 5.,
            "contract_line_id": self.acct_line.id,
            "condition": "no_issue_to_date",
        })

        # Test without penalty
        self.assertFalse(self.contract.contractual_issue_ids)
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": "task1",
            "penalty_exemption": True,
            "contractual_issue_date": self.contract.date_start,
        })

        inv1 = self.contract.recurring_create_invoice()
        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [5.])

        # Add a penalty
        self.contract.contractual_issue_ids |= self.env['project.task'].create({
            "name": "task2",
            "penalty_exemption": False,
            "contractual_issue_date": self.contract.date_start,
        })

        inv2 = self.contract.recurring_create_invoice()
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [0.])

    def test_min_end_contract_date(self):
        self.contract.update({
            'min_contract_duration': 2,
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
        })

        self.env['contract.discount.line'].create({
            "name": "Post commitment discount",
            "amount_type": "percent",
            "amount_value": 5.,
            "start_reference": "min_contract_end_date",
            "start_value": 1,
            "start_unit": "months",
            "end_type": "relative",
            "end_reference": "min_contract_end_date",
            "end_value": 4,
            "end_unit": "months",
            "contract_line_id": self.acct_line.id,
        })

        self.assertEqual(self.contract.min_contract_end_date, "2016-04-15")

        expected = [("2016-02-29", 0.), ("2016-03-29", 0.), ("2016-04-29", 0.),
                    ("2016-05-29", 5.), ("2016-06-29", 5.), ("2016-07-29", 5.),
                    ("2016-08-29", 0.), ("2016-09-29", 0.)]

        for date, discount in expected:
            inv = self.contract.recurring_create_invoice()
            self.assertEqual(inv.date_invoice, date)
            self.assertEqual(inv.mapped("invoice_line_ids.discount"),
                             [discount], "incorrect discount at %s" % date)


class CouponConditionTC(ContractSaleWithCouponTC):

    def test(self):
        create_invoice = self.contract.recurring_create_invoice

        # Default tax is 15%
        self.assertEqual(create_invoice().amount_total, 6.9)
        self.assertEqual(create_invoice().amount_total, 6.9)
        self.assertEqual(create_invoice().amount_total, 6.9)
        self.assertEqual(create_invoice().amount_total, 34.5)
