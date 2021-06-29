from os import path as osp
from datetime import date

from mock import patch

from odoo.addons.contract_variable_discount.models.contract import Contract

from odoo.addons.contract.tests.test_contract import TestContractBase
from odoo.exceptions import ValidationError
from odoo import fields


HERE = osp.abspath(osp.dirname(__file__))

SIMPLE_FORMULA = u"""
Fix discount:
  amount:
    type: fix
    value: 2
"""


CONDITIONAL_FORMULA = u"""
Fix discount after 1 month under condition:
  condition: test
  amount:
    type: percent
    value: 5
  start:
    reference: date_start
    value: 1
    unit: months
"""


class ContractTC(TestContractBase):

    def set_discount_formula(self, formula):
        self.acct_line.update({'discount_formula': formula})

    def set_discount_formula_from_file(self, fname):
        with open(osp.join(HERE, "data", fname)) as fobj:
            self.set_discount_formula(fobj.read().decode("utf-8"))

    def check_discounts(self, expected_discounts):
        for date, expected in sorted(expected_discounts):
            while self.contract.recurring_next_date <= date:
                invoice = self.contract.recurring_create_invoice()
                # print "DEBUG: invoice date = %s" % invoice.date_invoice
                if invoice.date_invoice == date:
                    actual = invoice.mapped('invoice_line_ids.discount')
                    self.assertEqual(actual, [expected],
                        "Incorrect discount %s (expected: %s) at %s" % (
                            actual, [expected], date))
                    break
            else:
                raise ValueError('Expected inv date %s never reached' % date)

    def test_discount_formula_validation(self):
        invalid_yaml = u"a: 1\n- invalid"

        with self.assertRaises(ValidationError) as err:
            self.set_discount_formula(invalid_yaml)
        self.assertIn(u"Invalid YAML", err.exception[0])

        with self.assertRaises(ValidationError) as err:
            self.acct_line.copy({'discount_formula': invalid_yaml})
        self.assertIn(u"Invalid YAML", err.exception[0])

    def _discount_date(self, formula, date_invoice=None):
        return self.contract._discount_formula_date(
            self.acct_line, date_invoice, formula)

    def test_discount_formula_date_ok(self):
        self.assertEqual(self._discount_date({
            "reference": "date_start",
            "unit": "days",
            "value": 5,
        }), date(2016, 2, 20))

        # reference default to "date_start"
        self.assertEqual(self._discount_date({
            "unit": "weeks",
            "value": 3,
        }), date(2016, 3, 7))

        self.assertEqual(self._discount_date({
            "unit": "months",
            "value": 2,
        }), date(2016, 4, 15))

        self.assertEqual(self._discount_date({
            "unit": "years",
            "value": 3,
        }), date(2019, 2, 15))

    def _check_formula_date_error(self, date_descr, expected_error):
        with self.assertRaises(ValidationError) as err:
            self._discount_date(date_descr)
        self.assertIn(expected_error, err.exception.args[0])

    def test_discount_formula_date_errors(self):
        self._check_formula_date_error({
            "reference": "does_not_exist",
            "unit": "days",
            "value": 5,
            }, "Incorrect reference 'does_not_exist'")

        self._check_formula_date_error({
            "reference": "date_end",
            "unit": "days",
            "value": 5,
            }, "Incorrect reference date value")

        self._check_formula_date_error({"value": 5}, "Missing unit")
        self._check_formula_date_error({"unit": "does_not_exist", "value": 5},
                                       "Invalid unit")

        self._check_formula_date_error({"unit": "days"}, "Missing value")

        self._check_formula_date_error({"unit": "days", "value": "wrong"},
                                       "Invalid value")

    def test_discount_amount_type_error(self):
        self.set_discount_formula(SIMPLE_FORMULA.replace('fix', 'not_exist'))
        with self.assertRaises(ValidationError) as err:
            self.contract.recurring_create_invoice()

        self.assertIn("Invalid discount formula amount type 'not_exist'",
                      err.exception.args[0])

    def test_discount_formula_compute_0(self):
        self.set_discount_formula(SIMPLE_FORMULA)
        invoice = self.contract.recurring_create_invoice()
        self.assertEqual(invoice.mapped("invoice_line_ids.discount"), [2.])

    def test_discount_formula_compute_1(self):
        self.set_discount_formula_from_file("discount_1.yaml")
        self.check_discounts([
            ('2016-02-29', 5.),
            ('2018-01-28', 5.),
            ('2018-02-28', 15.),
            ('2019-01-28', 15.),
            ('2019-02-28', 25.),
            ('2020-03-28', 25.),
        ])

    def test_formula_propagation(self):
        "Check the formula on contract template is copied to new contracts"

        # Add a line with a discount formula on contract template
        line_vals = self.line_vals.copy()
        line_vals.update({
            'analytic_account_id': self.template.id,
            'discount_formula': SIMPLE_FORMULA,
        })
        self.env['account.analytic.contract.line'].create(line_vals)

        # Use this template as the model for self.contract:
        self.contract.recurring_invoice_line_ids.unlink()
        self.contract.contract_template_id = self.template
        self.contract._onchange_contract_template_id()

        # Check the discount formula was propagated
        self.assertEqual(
            self.contract.mapped('recurring_invoice_line_ids.discount_formula'),
            [SIMPLE_FORMULA])

    def test_condition_and_description(self):
        self.set_discount_formula(CONDITIONAL_FORMULA)

        method = "_discount_formula_condition_test"
        with patch.object(Contract, method, create=True) as mock:
            mock.return_value = True
            inv1 = self.contract.recurring_create_invoice()
            inv2 = self.contract.recurring_create_invoice()

        self.assertEqual(mock.call_count, 2)
        self.assertEqual([tuple(c) for c in mock.call_args_list], [
            ((self.acct_line, fields.Date.from_string(inv1.date_invoice)), {}),
            ((self.acct_line, fields.Date.from_string(inv2.date_invoice)), {}),
        ])

        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [0.])
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [5.])

        self.assertEqual(inv1.mapped("invoice_line_ids.name"),
                         [u"Services from 02/29/2016 to 03/28/2016"])
        self.assertEqual(inv2.mapped("invoice_line_ids.name"),
                         [u"Services from 03/29/2016 to 04/28/2016\n"
                          u"Applied discounts:\n"
                          u"- Fix discount after 1 month under condition"])
