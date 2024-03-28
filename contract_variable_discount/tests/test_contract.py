from datetime import date

from mock import patch

from odoo import fields, models

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestConditionDiscountLine(models.Model):
    _inherit = "contract.discount.line"

    condition = fields.Selection(selection_add=[("test", "Test")])

    def _compute_condition_test(self, line, date_invoice):
        "Overriden by a mock"


class ContractTC(TestContractBase):
    @classmethod
    def _init_test_model(cls, model_cls):
        """Build a model from model_cls in order to test abstract models.
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
        model._setup_base()
        model._setup_fields()
        model._setup_complete()
        model._auto_init()
        model.init()
        return inst

    @classmethod
    def setUpClass(cls):
        super(ContractTC, cls).setUpClass()
        cls._init_test_model(TestConditionDiscountLine)
        # Adjust dates to our test needs:
        cls.contract.date_start = "2016-02-15"
        cls.contract.recurring_next_date = "2016-02-29"

    def tdiscount(self, ct_line=None, **kwargs):
        kwargs.setdefault("contract_template_line_id", ct_line.id)
        return self.env["contract.template.discount.line"].create(kwargs)

    def cdiscount(self, c_line=None, **kwargs):
        kwargs.setdefault("contract_line_id", (c_line or self.acct_line).id)
        return self.env["contract.discount.line"].create(kwargs)

    def set_cdiscounts(self, discounts):
        self.acct_line.specific_discount_line_ids = discounts

    def check_cdiscounts(self, expected_discounts):
        for discount_date, expected_value in sorted(expected_discounts):
            discount_date = fields.Date.from_string(discount_date)
            while self.contract.recurring_next_date <= discount_date:
                invoice = self.contract.recurring_create_invoice()
                if invoice.date_invoice == discount_date:
                    actual = invoice.mapped("invoice_line_ids.discount")
                    self.assertEqual(
                        actual,
                        [expected_value],
                        "Incorrect discount %s (expected: %s) at %s"
                        % (actual, [expected_value], discount_date),
                    )
                    break
            else:
                raise ValueError("Expected inv date %s never reached" % discount_date)

    def _discount_date(self, prefix="start", **kwargs):
        kwargs.setdefault("name", "Test discount")
        kwargs.setdefault("amount_value", 1.0)
        discount = self.cdiscount(**kwargs)
        return discount._compute_date(self.acct_line, prefix)

    def _check_applied_discounts(self, invl, prefix, ctd_names=(), cd_names=()):
        ctd_names, cd_names = list(ctd_names), list(cd_names)

        self.assertEqual(len(invl), 1)

        expected = prefix
        if ctd_names or cd_names:
            expected += "\n"
            expected += "\n- ".join(["Applied discounts:"] + ctd_names + cd_names)

        self.assertEqual(invl.name, expected)

        ctd_rel = "applied_discount_template_line_ids.name"
        cd_rel = "applied_discount_line_ids.name"
        self.assertEqual(invl.mapped(ctd_rel), ctd_names)
        self.assertEqual(invl.mapped(cd_rel), cd_names)

    def test_discount_compute_date_ok(self):
        "Start date must be computed correctly"
        self.assertEqual(
            self._discount_date(start_value=-5, start_unit="days"), date(2016, 2, 10)
        )
        self.assertEqual(
            self._discount_date(start_unit="weeks", start_value=3), date(2016, 3, 7)
        )
        self.assertEqual(
            self._discount_date(start_unit="months", start_value=2), date(2016, 4, 15)
        )
        self.assertEqual(
            self._discount_date(start_unit="years", start_value=3), date(2019, 2, 15)
        )
        self.assertEqual(
            self._discount_date(start_type="absolute", start_date="2021-07-17"),
            date(2021, 7, 17),
        )
        self.assertEqual(self._discount_date(prefix="start"), date(2016, 2, 15))
        self.assertIsNone(self._discount_date(prefix="end"))

    def test_discount_compute_0(self):
        self.set_cdiscounts(
            self.cdiscount(
                name="Fix discount",
                amount_type="fix",
                amount_value=2.0,
            )
        )
        invoice = self.contract.recurring_create_invoice()
        self.assertEqual(invoice.mapped("invoice_line_ids.discount"), [2.0])

    def _discounts_1(self):
        return (
            self.cdiscount(
                name="Early adopter discount",
                amount_type="percent",
                amount_value=5.0,
            )
            | self.cdiscount(
                name="2 years loyalty",
                amount_type="percent",
                amount_value=10.0,
                start_reference="date_start",
                start_value=2,
                start_unit="years",
                end_type="relative",
                end_reference="date_start",
                end_value=3,
                end_unit="years",
            )
            | self.cdiscount(
                name="More than 3 years loyalty",
                amount_type="percent",
                amount_value=20.0,
                start_reference="date_start",
                start_value=3,
                start_unit="years",
            )
        )

    def test_discount_compute_1(self):
        self.set_cdiscounts(self._discounts_1())

        self.check_cdiscounts(
            [
                ("2016-02-29", 5.0),
                ("2018-01-28", 5.0),
                ("2018-02-28", 15.0),
                ("2019-01-28", 15.0),
                ("2019-02-28", 25.0),
                ("2020-03-28", 25.0),
            ]
        )

    def test_discount_override(self):
        "Discounts on contract template are handled but can be overidden"

        # Add a line with 2 discounts on a new contract template
        _vals = self.line_template_vals.copy()
        _vals["recurring_rule_type"] = "monthly"
        template = self.env["contract.template"].create(
            {
                "name": "Test Contract Template",
                "contract_line_ids": [
                    (0, 0, _vals),
                ],
            }
        )
        ct_line = template.contract_line_ids
        self.tdiscount(
            ct_line, name="Fix discount", amount_value=2.0, amount_type="fix"
        )
        tdiscount2 = self.tdiscount(
            ct_line, name="5% discount", amount_value=5.0, amount_type="percent"
        )

        # Use this template as the model for self.contract:
        self.contract.contract_line_ids.update({"is_canceled": True})
        self.contract.contract_line_ids.unlink()
        self.contract.contract_template_id = template
        self.contract._onchange_contract_template_id()
        self.contract.contract_line_ids.date_start = "2016-02-29"
        self.contract.contract_line_ids._onchange_date_start()
        self.contract._compute_date_end()  # Refresh contract start and end

        # Check applied discounts
        inv = self.contract.recurring_create_invoice()
        self._check_applied_discounts(
            inv.invoice_line_ids,
            "Services from 02/29/2016 to 03/28/2016",
            ["Fix discount", "5% discount"],
        )

        # Add an override for the 5% discount
        self.cdiscount(
            self.contract.contract_line_ids,
            name="10% discount",
            amount_type="percent",
            amount_value=10.0,
            replace_discount_line_id=tdiscount2.id,
        )

        # Check applied discounts
        inv = self.contract.recurring_create_invoice()
        self._check_applied_discounts(
            inv.invoice_line_ids,
            "Services from 03/29/2016 to 04/28/2016",
            ["Fix discount"],
            ["10% discount"],
        )

    def test_condition_and_description(self):
        self.set_cdiscounts(
            self.cdiscount(
                name="Fix discount after 1 month under condition",
                condition="test",
                amount_value=5.0,
                amount_type="percent",
                start_reference="date_start",
                start_value=1,
                start_unit="months",
            )
        )

        with patch.object(
            TestConditionDiscountLine, "_compute_condition_test", create=True
        ) as mock:

            mock.return_value = True
            inv1 = self.contract.recurring_create_invoice()
            inv2 = self.contract.recurring_create_invoice()

            mock.return_value = False
            inv3 = self.contract.recurring_create_invoice()

        self.assertEqual(mock.call_count, 3)
        self.assertEqual(
            [tuple(c) for c in mock.call_args_list],
            [
                ((self.acct_line, fields.Date.from_string(inv1.date_invoice)), {}),
                ((self.acct_line, fields.Date.from_string(inv2.date_invoice)), {}),
                ((self.acct_line, fields.Date.from_string(inv3.date_invoice)), {}),
            ],
        )

        self.assertEqual(inv1.mapped("invoice_line_ids.discount"), [0.0])
        self.assertEqual(inv2.mapped("invoice_line_ids.discount"), [5.0])
        self.assertEqual(inv3.mapped("invoice_line_ids.discount"), [0.0])

        self._check_applied_discounts(
            inv1.invoice_line_ids,
            "Services from 02/15/2016 to 03/28/2016",
        )

        self._check_applied_discounts(
            inv2.invoice_line_ids,
            "Services from 03/29/2016 to 04/28/2016",
            [],
            ["Fix discount after 1 month under condition"],
        )

        self._check_applied_discounts(
            inv3.invoice_line_ids, "Services from 04/29/2016 to 05/28/2016"
        )
