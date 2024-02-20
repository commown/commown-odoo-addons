from datetime import date, datetime

import pyexcel
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError

from .common import RentalFeesTC


class RentalFeesComputationTC(RentalFeesTC):
    maxDiff = None

    def setUp(self):
        super().setUp()

        ref = self.env.ref

        fees_product = self.env["product.template"].create(
            {"name": "fees", "type": "service", "list_price": 0.0}
        )

        supplier_account = self.env["account.account"].create(
            {
                "code": "cust_acc",
                "name": "customer account",
                "user_type_id": ref("account.data_account_type_payable").id,
                "reconcile": True,
            }
        )

        expenses_account = self.env["account.account"].create(
            {
                "code": "rev_exp",
                "name": "expences account",
                "user_type_id": ref("account.data_account_type_expenses").id,
            }
        )

        tax = self.env["account.tax"].create(
            {
                "amount": 10.0,
                "amount_type": "percent",
                "price_include": False,
                "name": "Test tax",
                "type_tax_use": "sale",
            }
        )

        inv_model = self.env["account.invoice"].create(
            {
                "type": "in_invoice",
                "partner_id": self.po.partner_id.id,
                "account_id": supplier_account.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": fees_product.product_variant_id.id,
                            "name": "Rental fees until ##DATE##",
                            "price_unit": 0.0,
                            "account_id": expenses_account.id,
                            "invoice_line_tax_ids": [(6, 0, tax.ids)],
                        },
                    )
                ],
            }
        )

        self.fees_def.model_invoice_id = inv_model.id

        self.expenses_journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "TJ",
                "company_id": self.env.user.company_id.id,
                "type": "bank",
                "update_posted": True,
            }
        )

    def compute(self, until_date, fees_def=None, run=True, invoice=False):
        fees_def = fees_def or self.fees_def

        computation = self.env["rental_fees.computation"].create(
            {
                "fees_definition_ids": [(6, 0, fees_def.ids)],
                "until_date": until_date,
            }
        )

        if run:
            computation.action_run()

        if invoice:
            computation.action_invoice()

        return computation

    def pay_supplier_invoice(self, supplier_invoice):
        self.env["account.payment"].create(
            {
                "company_id": self.env.user.company_id.id,
                "partner_id": supplier_invoice.partner_id.id,
                "partner_type": "supplier",
                "state": "draft",
                "payment_type": "outbound",
                "journal_id": self.expenses_journal.id,
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_out"
                ).id,
                "amount": supplier_invoice.amount_total,
                "currency_id": supplier_invoice.currency_id.id,
                "invoice_ids": [(6, 0, [supplier_invoice.id])],
            }
        ).post()

    def test_open_job(self):
        "Method open job should"
        old_env = self.env
        try:
            self.env = self.env(context=dict(test_queue_job_no_delay=False))
            comp = self.compute("2021-01-31")
        finally:
            self.env = old_env

        self.assertEqual(comp.state, "running")

        action1 = comp.button_open_job()
        self.assertEqual(action1["res_model"], "queue.job")
        job = self.env[action1["res_model"]].browse(action1["res_id"])

        action2 = job.open_related_action()
        self.assertEqual(action2["res_model"], "rental_fees.computation")
        self.assertEqual(comp, self.env[action2["res_model"]].browse(action2["res_id"]))

    def pay_customer_invoice(self, invoice):
        journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
        apm = self.env.ref("account.account_payment_method_manual_in")

        invoice.action_invoice_open()
        payment = self.env["account.payment"].create(
            {
                "company_id": self.env.user.company_id.id,
                "partner_id": invoice.partner_id.id,
                "partner_type": "customer",
                "state": "draft",
                "payment_type": "inbound",
                "journal_id": journal.id,
                "payment_method_id": apm.id,
                "amount": invoice.residual,
                "currency_id": invoice.currency_id.id,
                "invoice_ids": [(6, 0, [invoice.id])],
                "payment_date": invoice.date_invoice,
            }
        )
        payment.post()
        self.assertEqual(invoice.state, "paid")

    def create_invoices_until(self, contract, until_date, pay=True):
        invoices = self.env["account.invoice"]
        until_date = fields.Date.from_string(until_date)
        while contract.recurring_next_date <= until_date:
            inv = contract._recurring_create_invoice()
            if pay:
                self.pay_customer_invoice(inv)
            invoices |= inv
        return invoices

    def test_compute_and_invoicing_and_reporting(self):
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract1, date="2021-02-15")
        contract1.date_start = "2021-02-15"

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 2", contract=contract2, date="2021-03-06")
        contract2.date_start = "2021-03-06"

        device2 = contract2.quant_ids.lot_id
        self.scrap_device(device2, date(2021, 4, 5))

        self.create_invoices_until(contract1, "2021-05-01")
        self.create_invoices_until(contract2, "2021-05-01")

        c1 = self.compute("2021-01-31", invoice=True)
        self.assertEqual(c1.fees, 0.0)
        self.assertIn("01/31/2021", c1.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c1.invoice_ids.amount_total, 0.0)
        c1.invoice_ids.action_invoice_open()

        c2 = self.compute("2021-02-28", invoice=True)
        self.assertEqual(c2.fees, 2.5)
        self.assertIn("02/28/2021", c2.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c2.invoice_ids.amount_total, 2.75)
        self.assertEqual(c2.invoice_ids.amount_tax, 0.25)
        c2.invoice_ids.action_invoice_open()

        c3 = self.compute("2021-03-31", invoice=True)
        self.assertEqual(c3.fees, 7.5)
        self.assertIn("03/31/2021", c3.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c3.invoice_ids.amount_total, 5.5)
        self.assertEqual(c3.invoice_ids.amount_tax, 0.5)
        c3.invoice_ids.action_invoice_open()

        c4 = self.compute("2021-04-30", invoice=True)
        self.assertEqual(c4.fees, 317.5)
        self.assertIn("04/30/2021", c4.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c4.invoice_ids.amount_total, 341.0)
        self.assertEqual(c4.invoice_ids.amount_tax, 31.0)
        c4.invoice_ids.action_invoice_open()
        compensations = c4.compensation_details()
        self.assertEqual(compensations.mapped("fees"), [300.0])

        # Paying an invoice, even after another one was emitted must work
        self.pay_supplier_invoice(c2.invoice_ids)
        self.assertEqual(c2.invoice_ids.state, "paid")

        # Adding an invoice while a later computation exists must raise
        with self.assertRaises(ValidationError) as err:
            c2.invoice_ids |= c2.invoice_ids.copy()
        self.assertEqual(
            "Operation not allowed: there are later fees computations with"
            " invoices which amount would become invalid.",
            err.exception.name,
        )

        # Same with the action_invoice method
        with self.assertRaises(UserError) as err:
            c2.action_invoice()
        self.assertEqual(
            "There is a later invoice for the same fees definition",
            err.exception.name,
        )

        # Invoicing requires a model: check this too
        with self.env.cr.savepoint():
            self.fees_def.model_invoice_id = False
            with self.assertRaises(UserError) as err:
                c5 = self.compute("2021-05-30", invoice=True)
        self.assertEqual(
            "Please set the invoice model on all fees definitions.",
            err.exception.name,
        )

        # Check computation comparison action does not crash
        compare_action = (c1 | c2).action_compare_computations()
        self.assertEqual(compare_action["type"], "ir.actions.act_window")
        self.assertEqual(compare_action["res_model"], "rental_fees.computation.detail")

        # Generate an ods report
        ref = self.env.ref
        action = ref("rental_fees.action_py3o_spreadsheet_fees_rental_computation")
        ods = pyexcel.get_book(file_content=action.render(c4.ids)[0], file_type="ods")
        self.assertEquals(
            ods.sheet_names(),
            [
                "Global figures",
                "Detailed rental fees",
                "Detailed compensations",
                "Per device revenues",
            ],
        )

        # Check the summary sheet:
        s_sum = ods.sheet_by_name("Global figures")

        # - Until date
        self.assertEquals(s_sum[8, 2], "Situation at date: 04/30/2021")

        # - Amounts per fees definition
        expected = {
            "Agreement": "Test fees_def",
            "Rental fees since the beginning": 17.5,
            "Compensation fees since the beginning": 300,
            "Already invoiced since the beginning": 7.5,
            "Fees to be invoiced": 310.0,
        }
        self.assertEquals(dict(zip(s_sum.row[10][2:7], s_sum.row[11][2:7])), expected)
        # - Amount totals
        expected["Agreement"] = "Totals"
        self.assertEquals(dict(zip(s_sum.row[10][2:7], s_sum.row[12][2:7])), expected)

        # - Devices per fees def
        expected = {
            "Agreement": "Test fees_def",
            "Nb of devices under agreement": 3,
            "Nb of devices that generated fees": 1,
            "Nb of devices no longer operable": 1,
            "Nb of devices generating fees": 1,
        }
        self.assertEquals(dict(zip(s_sum.row[14][2:7], s_sum.row[15][2:7])), expected)
        # - Devices totals
        expected["Agreement"] = "Totals"
        self.assertEquals(dict(zip(s_sum.row[14][2:7], s_sum.row[16][2:7])), expected)

        s_dev = ods.sheet_by_name("Per device revenues")
        product_col = [c for c in s_dev.column[3] if c != "" and type(c) == str]
        self.assertEquals(product_col, ["Product"] + 3 * ["Fairphone 3"])

    def test_send_report_for_invoicing(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        comp = self.compute("2022-03-01")
        comp.action_send_report_for_invoicing()

        self.assertEqual(comp.mapped("invoice_ids.state"), ["draft"])
        inv = comp.invoice_ids
        self.assertEqual(
            inv.message_ids[0].subject,
            "[YourCompany] Fees to be invoices as of 03/01/2022",
        )
        atts = inv.message_ids[0].attachment_ids
        self.assertEqual(
            atts.mapped("mimetype"),
            ["application/vnd.oasis.opendocument.spreadsheet"],
        )

    def test_merged_invoices(self):
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract1, date="2021-02-15")
        contract1.date_start = "2021-02-15"

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 2", contract=contract2, date="2021-03-06")
        contract2.date_start = "2021-03-06"

        computation_date = "2021-03-31"
        invoices = self.create_invoices_until(contract1, computation_date, pay=False)
        invoices |= self.create_invoices_until(contract2, computation_date, pay=False)
        invoices_info = invoices.do_merge(date_invoice=computation_date)

        self.assertEqual(len(invoices_info), 1)
        self.assertEqual(list(invoices_info.values())[0], invoices.ids)
        merged_inv = self.env["account.invoice"].browse(list(invoices_info))
        self.pay_customer_invoice(merged_inv)

        c3 = self.compute(computation_date)
        self.assertEqual(c3.fees, 7.5)

    def test_action_invoice_two_fees_def(self):
        p2 = self.storable_product.copy()
        fees_def2 = self.fees_def.copy({"name": "def2", "product_template_id": p2.id})

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        fees_def = self.fees_def | fees_def2
        comp = self.compute("2022-03-01", fees_def=fees_def, invoice=True)
        self.assertEqual(len(comp.mapped("invoice_ids.invoice_line_ids")), 2)

    def test_compute_with_forecast(self):
        company = self.env.user.partner_id.company_id
        company.update(
            {
                "enable_contract_forecast": True,
                "contract_forecast_interval": 60,
                "contract_forecast_rule_type": "monthly",
            }
        )

        # Do not choose plain today to make test deterministic:
        # - always have a last month with no fees
        # - avoid end of month invoice date shifts
        base_date = date.today() - relativedelta(days=7)
        if base_date.day > 27:
            base_date = date(base_date.year, base_date.month, 27)

        start_date = base_date - relativedelta(months=3, days=-1)
        send_datetime = datetime(*start_date.timetuple()[:-2])
        compute_date = base_date + relativedelta(months=36)

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract, date=send_datetime)
        contract.date_start = start_date
        self.create_invoices_until(contract, base_date)

        computation = self.compute(compute_date)

        def months_from_start(date):
            "Return number of months between contract start date and given date"
            delta = relativedelta(date, contract.date_start)
            return delta.years * 12 + delta.months

        def fees_descr(details):
            "Return a short tuple description of given computation details"
            aday = relativedelta(days=1)
            for detail in details:
                yield (
                    months_from_start(detail.from_date),
                    months_from_start(detail.to_date + aday),
                    detail.fees,
                    detail.fees_definition_line_id.sequence,
                )

        forecast_fees = computation.detail_ids.filtered("is_forecast")
        actual_fees = computation.detail_ids - forecast_fees

        self.assertEqual(
            list(fees_descr(actual_fees)),
            [(0, 1, 2.50, 1), (1, 2, 2.50, 1), (2, 3, 12.50, 2), (3, 4, 0.0, 2)],
        )

        # Warning: in the test setup, the contract line tax has price_include=True
        # As a consequence, the contract forecast are NOT without tax here...
        self.assertEqual(
            list(fees_descr(forecast_fees)),
            [(3, 4, 15.0, 2), (4, 5, 0.0, 2)]
            + [(i, i + 1, 1.5, 100) for i in range(5, 39)],
        )

    def test_cannot_modify_important_def_fields_with_computation(self):
        "Cannot modify a fees def which has a non-draft computation"

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract, date="2021-02-15")
        contract.date_start = "2021-02-15"
        inv = contract._recurring_create_invoice()
        self.pay_customer_invoice(inv)

        # Can modify while computation is draft:
        computation = self.compute("2021-03-01", run=False)
        self.assertEqual(computation.state, "draft")

        new_fees_def_line = self.env["rental_fees.definition_line"].create(
            {
                "fees_definition_id": self.fees_def.id,
                "sequence": 20,
                "duration_value": 10,
                "duration_unit": "months",
                "fees_type": "proportional",
                "monthly_fees": 0.4,
            }
        )
        self.fees_def.line_ids |= new_fees_def_line

        # Modifications are restricted once computation is done,
        # so check the test prerequisites
        computation._run()
        self.assertEqual(computation.state, "done")
        self.assertTrue(
            computation.detail_ids.filtered(
                lambda d: d.lot_id.name == "N/S 1" and d.fees > 0
            )
        )

        # - modifying the name should be OK
        self.fees_def.name = "Changed name"

        # - but not product_template_id or partner_id
        expected_msg = "Some non-draft computations use this fees definition."

        with self.assertRaises(ValidationError) as err:
            pt_ref = "product.product_product_1_product_template"
            self.fees_def.product_template_id = self.env.ref(pt_ref).id
        self.assertIn(expected_msg, err.exception.name)

        with self.assertRaises(ValidationError) as err:
            partner_ref = "base.res_partner_1"
            self.fees_def.partner_id = self.env.ref(partner_ref).id
        self.assertIn(expected_msg, err.exception.name)

    def test_compute_no_rental_compensation_zero_1(self):
        "No rental conditions check: A first rental is required"
        comp = self.compute("2022-01-01")
        self.assertFalse(comp.details("no_rental_compensation").mapped("fees"))

    def test_compute_no_rental_compensation_zero_2(self):
        "No rental conditions check: within defined penalty period"
        contract = self.env["contract.contract"].of_sale(self.so)[0]

        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.receive_device("N/S 1", contract, "2021-07-02")
        contract.end_date = "2021-07-02"

        comp = self.compute("2022-02-01")
        self.assertFalse(comp.details("no_rental_compensation").mapped("fees"))

    def test_compute_no_rental_compensation_zero_3(self):
        "No rental conditions check: rented again before the limit"
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract1, "2021-02-01")
        contract1.date_start = "2021-02-01"
        self.receive_device("N/S 1", contract1, "2021-03-15")
        contract1.end_date = "2021-03-15"

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 1", contract2, "2021-09-14")
        contract2.date_start = "2021-09-14"
        self.receive_device("N/S 1", contract2, "2021-09-14")
        contract2.end_date = "2021-09-14"

        comp = self.compute("2021-10-01")
        self.assertFalse(comp.details("no_rental_compensation").mapped("fees"))

    def test_compute_no_rental_compensation_non_zero_1(self):
        "No rental conditions fulfilled: compensation occurs, then no more fees"
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract1, "2021-02-01")
        contract1.date_start = "2021-02-01"
        while contract1.recurring_next_date <= date(2021, 4, 1):
            contract1._recurring_create_invoice()
        self.receive_device("N/S 1", contract1, "2021-04-01")
        contract1.end_date = "2021-04-01"

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 1", contract2, "2022-02-01")
        contract2.date_start = "2022-02-01"
        while contract2.recurring_next_date <= date(2022, 4, 1):
            contract2._recurring_create_invoice()

        comp = self.compute("2022-04-01")
        self.assertEqual(comp.details("no_rental_compensation").mapped("fees"), [300.0])
        self.assertFalse(comp.rental_details().mapped("fees"))

    def test_compute_no_rental_compensation_non_zero_2(self):
        "No rental then lost lead to exactly one compensation"

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        device = contract.quant_ids.ensure_one().lot_id
        while contract.recurring_next_date <= date(2021, 4, 1):
            contract._recurring_create_invoice()
        self.receive_device("N/S 1", contract, "2021-04-01")
        contract.end_date = "2021-04-01"

        self.scrap_device(device, date(2021, 12, 1))  # after no rental limit!

        comp = self.compute("2022-04-01")
        self.assertEqual(comp.compensation_details().mapped("fees"), [300.0])
        self.assertFalse(comp.rental_details().mapped("fees"))

    def test_compute_excluded_device(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        device = contract.quant_ids.ensure_one().lot_id
        while contract.recurring_next_date <= date(2021, 3, 1):
            contract._recurring_create_invoice()

        reason = "Used by an internal employee"
        self.env["rental_fees.excluded_device"].create(
            {
                "fees_definition_id": self.fees_def.id,
                "device": device.id,
                "reason": reason,
            }
        )

        comp = self.compute("2022-03-01")
        self.assertEqual(
            comp.details("excluded_device_compensation").mapped("fees"),
            [300.0],
        )

    def test_compute_monthly_fees_error_main_rental_line(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        rental_service = contract.get_main_rental_service()

        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-05-01")

        # Check the computation is OK when no error is raised
        comp = self.compute("2021-05-01")
        self.assertTrue(comp.fees > 0)

        # Do the same computation but with an error in get_main_rental_service:
        rental_service.property_contract_template_id = False
        with self.assertRaises(RuntimeError) as err:
            self.compute("2021-05-01")

        # Check the generated error contains useful information
        exc = str(err.exception)
        self.assertIn("device: N/S 1", exc)
        self.assertIn(contract.name, exc)
        self.assertIn(self.fees_def.name, exc)

    def test_fees_def_split_dates(self):
        self.assertEqual(
            {
                date(2021, 3, 10): self.fees_def.line_ids[0],
                date(2021, 6, 10): self.fees_def.line_ids[1],
                None: self.fees_def.line_ids[2],
            },
            self.compute("2100-01-01")._fees_def_split_dates(
                self.fees_def, date(2021, 1, 10)
            ),
        )

    def test_split_periods_wrt_fees_def_1(self):
        periods = [
            {
                "from_date": date(2021, 1, 10),
                "to_date": date(2021, 2, 15),
                "contract": 0,
                "is_forecast": False,
            },
            {
                "from_date": date(2021, 3, 15),
                "to_date": date(2021, 4, 15),
                "contract": 1,
                "is_forecast": False,
            },
        ]

        self.assertEqual(
            [
                {
                    "contract": 0,
                    "from_date": date(2021, 1, 10),
                    "to_date": date(2021, 2, 15),
                    "fees_def_line": self.fees_def.line_ids[0],
                    "is_forecast": False,
                },
                {
                    "contract": 1,
                    "from_date": date(2021, 3, 15),
                    "to_date": date(2021, 4, 15),
                    "fees_def_line": self.fees_def.line_ids[1],
                    "is_forecast": False,
                },
            ],
            self.compute("2100-01-01").split_periods_wrt_fees_def(
                self.fees_def, periods
            ),
        )

    def test_split_periods_wrt_fees_def_2(self):
        periods = [
            {
                "from_date": date(2021, 1, 10),
                "to_date": date(2021, 6, 30),
                "contract": 0,
                "is_forecast": False,
            },
            {
                "from_date": date(2021, 7, 15),
                "to_date": date(2021, 12, 5),
                "contract": 1,
                "is_forecast": False,
            },
        ]

        self.assertEqual(
            [
                {
                    "contract": 0,
                    "from_date": date(2021, 1, 10),
                    "to_date": date(2021, 3, 10),
                    "fees_def_line": self.fees_def.line_ids[0],
                    "is_forecast": False,
                },
                {
                    "contract": 0,
                    "from_date": date(2021, 3, 10),
                    "to_date": date(2021, 6, 10),
                    "fees_def_line": self.fees_def.line_ids[1],
                    "is_forecast": False,
                },
                {
                    "contract": 0,
                    "from_date": date(2021, 6, 10),
                    "to_date": date(2021, 6, 30),
                    "fees_def_line": self.fees_def.line_ids[2],
                    "is_forecast": False,
                },
                {
                    "contract": 1,
                    "from_date": date(2021, 7, 15),
                    "to_date": date(2021, 12, 5),
                    "fees_def_line": self.fees_def.line_ids[2],
                    "is_forecast": False,
                },
            ],
            self.compute("2100-01-01").split_periods_wrt_fees_def(
                self.fees_def, periods
            ),
        )

    def test_action_invoice_error(self):
        "All computation fees defs must have the same invoice model to be invoiceable"
        p2 = self.storable_product.copy()
        inv_model = self.fees_def.model_invoice_id.copy()
        fees_def2 = self.fees_def.copy(
            {
                "name": "def2",
                "product_template_id": p2.id,
                "model_invoice_id": inv_model.id,
            }
        )

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        comp = self.compute("2022-03-01", fees_def=self.fees_def | fees_def2)

        with self.assertRaises(UserError) as err:
            comp.action_invoice()
        self.assertEqual(
            err.exception.name,
            "Please use the same invoice model on all fees definition.",
        )
