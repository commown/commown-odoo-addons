# coding: utf-8

from datetime import date

import lxml.html
from mock import patch

from odoo.addons.contract.tests.test_contract import TestContractBase
from odoo import fields, models


class TestConditionDiscountLine(models.Model):
    _inherit = 'contract.discount.line'

    condition = fields.Selection(selection_add=[('test', "Test")])

    def _compute_condition_test(self, line, date_invoice):
        "Overriden by a mock"


class ContractTC(TestContractBase):

    @classmethod
    def _init_test_model(cls, model_cls):
        """ Build a model from model_cls in order to test abstract models.
        Note that this does not actually create a table in the database, so
        there may be some unidentified edge cases.
        Args:
            model_cls (openerp.models.BaseModel): Class of model to initialize
        Returns:
            model_cls: Instance
        """
        registry = cls.env.registry
        cr = cls.env.cr
        inst = model_cls._build_model(registry, cr)
        model = cls.env[model_cls._inherit].with_context(todo=[])
        model._prepare_setup()
        model._setup_base(partial=False)
        model._setup_fields(partial=False)
        model._setup_complete()
        model._auto_init()
        model.init()
        model._auto_end()
        return inst

    @classmethod
    def setUpClass(cls):
        super(ContractTC, cls).setUpClass()
        cls._init_test_model(TestConditionDiscountLine)

    def tdiscount(self, ct_line=None, **kwargs):
        kwargs.setdefault("contract_template_line_id", ct_line.id)
        return self.env['contract.template.discount.line'].create(kwargs)

    def cdiscount(self, c_line=None, **kwargs):
        kwargs.setdefault("contract_line_id", (c_line or self.acct_line).id)
        return self.env['contract.discount.line'].create(kwargs)

    def set_cdiscounts(self, discounts):
        self.acct_line.specific_discount_line_ids = discounts

    def check_cdiscounts(self, expected_discounts):
        for discount_date, expected_value in sorted(expected_discounts):
            while self.contract.recurring_next_date <= discount_date:
                invoice = self.contract.recurring_create_invoice()
                if invoice.date_invoice == discount_date:
                    actual = invoice.mapped('invoice_line_ids.discount')
                    self.assertEqual(
                        actual, [expected_value],
                        "Incorrect discount %s (expected: %s) at %s" % (
                            actual, [expected_value], discount_date))
                    break
            else:
                raise ValueError(
                    'Expected inv date %s never reached' % discount_date)

    def _discount_date(self, prefix=u"start", **kwargs):
        kwargs.setdefault("name", u"Test discount")
        kwargs.setdefault("amount_value", 1.)
        discount = self.cdiscount(**kwargs)
        return discount._compute_date(self.acct_line, prefix)

    def test_discount_compute_date_ok(self):
        "Start date must be computed correctly"
        self.assertEqual(
            self._discount_date(start_value=-5, start_unit="days"),
            date(2016, 2, 10))
        self.assertEqual(
            self._discount_date(start_unit="weeks", start_value=3),
            date(2016, 3, 7))
        self.assertEqual(
            self._discount_date(start_unit="months", start_value=2),
            date(2016, 4, 15))
        self.assertEqual(
            self._discount_date(start_unit="years", start_value=3),
            date(2019, 2, 15))
        self.assertEqual(
            self._discount_date(start_type="absolute", start_date="2021-07-17"),
            date(2021, 7, 17))
        self.assertEqual(
            self._discount_date(prefix="start"),
            date(2016, 2, 15))
        self.assertIsNone(self._discount_date(prefix="end"))

    def test_discount_compute_0(self):
        self.set_cdiscounts(self.cdiscount(
            name=u"Fix discount",
            amount_type=u"fix",
            amount_value=2.,
        ))
        invoice = self.contract.recurring_create_invoice()
        self.assertEqual(invoice.mapped("invoice_line_ids.discount"), [2.])

    def _discounts_1(self):
        return (
            self.cdiscount(
                name=u"Early adopter discount",
                amount_type="percent",
                amount_value=5.,
            ) | self.cdiscount(
                name=u"2 years loyalty",
                amount_type="percent",
                amount_value=10.,
                start_reference=u"date_start",
                start_value=2,
                start_unit=u"years",
                end_type=u"relative",
                end_reference=u"date_start",
                end_value=3,
                end_unit=u"years",
            ) | self.cdiscount(
                name=u"More than 3 years loyalty",
                amount_type="percent",
                amount_value=20.,
                start_reference=u"date_start",
                start_value=3,
                start_unit=u"years",
            )
        )

    def test_discount_compute_1(self):
        self.set_cdiscounts(self._discounts_1())

        self.check_cdiscounts([
            ('2016-02-29', 5.),
            ('2018-01-28', 5.),
            ('2018-02-28', 15.),
            ('2019-01-28', 15.),
            ('2019-02-28', 25.),
            ('2020-03-28', 25.),
        ])

    def test_discount_override(self):
        " Discounts on contract template are handled but can be overidden "

        # Add a line with 2 discounts on contract template
        _vals = self.line_vals.copy()
        _vals["analytic_account_id"] = self.template.id
        ct_line = self.env['account.analytic.contract.line'].create(_vals)

        self.tdiscount(ct_line, name=u"Fix discount",
                       amount_value=2., amount_type=u"fix")
        tdiscount2 = self.tdiscount(ct_line, name=u"5% discount",
                                    amount_value=5., amount_type=u"percent")

        # Use this template as the model for self.contract:
        self.contract.recurring_invoice_line_ids.unlink()
        self.template.update({"recurring_interval": 1,
                              "recurring_rule_type": "monthly"})
        self.contract.contract_template_id = self.template
        self.contract._onchange_contract_template_id()

        # Check applied discounts
        self.env["ir.translation"].load_module_terms(
            ["contract_variable_discount"],
            ["fr_FR"],
        )
        self.contract.partner_id.lang = u'fr_FR'
        inv = self.contract.recurring_create_invoice()
        self.assertEqual(inv.mapped("invoice_line_ids.name"),
                         [u"Services from 29/02/2016 to 28/03/2016\n"
                          u"Remises appliquées :\n"
                          u"- Fix discount\n"
                          u"- 5% discount"])

        # Add an override for the 5% discount
        self.cdiscount(
            self.contract.recurring_invoice_line_ids,
            name=u"10% discount", amount_type="percent", amount_value=10.,
            replace_discount_line_id=tdiscount2.id)

        # Check applied discounts
        inv = self.contract.recurring_create_invoice()
        self.assertEqual(inv.mapped("invoice_line_ids.name"),
                         [u"Services from 29/03/2016 to 28/04/2016\n"
                          u"Remises appliquées :\n"
                          u"- Fix discount\n"
                          u"- 10% discount"])

    def test_condition_and_description(self):
        self.set_cdiscounts(self.cdiscount(
            name=u"Fix discount after 1 month under condition",
            condition=u"test",
            amount_value=5.,
            amount_type=u"percent",
            start_reference=u"date_start",
            start_value=1,
            start_unit=u"months",
        ))

        with patch.object(TestConditionDiscountLine,
                          "_compute_condition_test",
                          create=True) as mock:

            mock.return_value = True
            inv1 = self.contract.recurring_create_invoice()
            inv2 = self.contract.recurring_create_invoice()

            mock.return_value = False
            inv3 = self.contract.recurring_create_invoice()

        self.assertEqual(mock.call_count, 3)
        self.assertEqual([tuple(c) for c in mock.call_args_list], [
            ((self.acct_line, fields.Date.from_string(inv1.date_invoice)), {}),
            ((self.acct_line, fields.Date.from_string(inv2.date_invoice)), {}),
            ((self.acct_line, fields.Date.from_string(inv3.date_invoice)), {}),
        ])

        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [0.])
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [5.])
        self.assertEqual(inv3.mapped("invoice_line_ids.discount"), [0.])

        self.assertEqual(inv1.mapped("invoice_line_ids.name"),
                         [u"Services from 02/29/2016 to 03/28/2016"])
        self.assertEqual(inv2.mapped("invoice_line_ids.name"),
                         [u"Services from 03/29/2016 to 04/28/2016\n"
                          u"Applied discounts:\n"
                          u"- Fix discount after 1 month under condition"])
        self.assertEqual(inv3.mapped("invoice_line_ids.name"),
                         [u"Services from 04/29/2016 to 05/28/2016"])

    def test_simulate_payments(self):
        self.set_cdiscounts(self._discounts_1())

        self.contract.recurring_next_date = self.contract.date_start

        report = self.env.ref(
            "contract_variable_discount.report_simulate_payments_html")
        fragment = report.render({"docs": self.contract}, 'ir.qweb')

        html = ('<html><head><meta charset="utf-8"/></head>'
                '<body>%s<//body></html>' % fragment)
        doc = lxml.html.fromstring(html)

        # First column contains dates:
        self.assertEqual(
            doc.xpath("//tbody/tr/td[1][not(@colspan)]/text()"),
            ['2016-02-15', '2018-02-15', '2019-02-15'])

        # Fourth contains discounts:
        self.assertEqual(
            [n.text_content() for n in doc.xpath("//tbody/tr/td[4]")],
            [u"5.0 %", u"15.0 %", u"25.0 %"])
