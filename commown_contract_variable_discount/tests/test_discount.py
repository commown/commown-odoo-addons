from datetime import date

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
        self.assertFalse(self.contract.issue_ids)
        self.contract.issue_ids |= self.env['project.task'].create({
            "name": "task1",
            "penalty_exemption": True,
            "contractual_issue_date": self.contract.date_start,
        })

        inv1 = self.contract.recurring_create_invoice()
        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [5.])

        # Add a penalty
        self.contract.issue_ids |= self.env['project.task'].create({
            "name": "task2",
            "penalty_exemption": False,
            "contractual_issue_date": self.contract.date_start,
        })

        inv2 = self.contract.recurring_create_invoice()
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [0.])

    def test_commitment_end_date(self):
        self.contract.update({
            "commitment_period_number": 2,
            "commitment_period_type": "monthly",
        })

        self.env['contract.discount.line'].create({
            "name": "Post commitment discount",
            "amount_type": "percent",
            "amount_value": 5.,
            "start_reference": "commitment_end_date",
            "start_value": 1,
            "start_unit": "months",
            "end_type": "relative",
            "end_reference": "commitment_end_date",
            "end_value": 4,
            "end_unit": "months",
            "contract_line_id": self.acct_line.id,
        })

        self.assertEqual(self.contract.commitment_end_date, date(2018, 3, 1))

        expected = [(date(2018, 1, 15), 0.), (date(2018, 2, 15), 0.),
                    (date(2018, 3, 15), 0.), (date(2018, 4, 15), 5.),
                    (date(2018, 5, 15), 5.), (date(2018, 6, 15), 5.),
                    (date(2018, 7, 15), 0.), (date(2018, 8, 15), 0.),
                    ]

        for _date, discount in expected:
            inv = self.contract.recurring_create_invoice()
            self.assertEqual(inv.date_invoice, _date)
            self.assertEqual(inv.mapped("invoice_line_ids.discount"),
                             [discount], "incorrect discount at %s" % _date)


class CouponConditionTC(ContractSaleWithCouponTC):

    def test(self):
        create_invoice = self.contract.recurring_create_invoice

        # Default tax is 15%
        self.assertEqual(create_invoice().amount_untaxed, 6.0)
        self.assertEqual(create_invoice().amount_untaxed, 6.0)
        self.assertEqual(create_invoice().amount_untaxed, 6.0)
        self.assertEqual(create_invoice().amount_untaxed, 30.0)
