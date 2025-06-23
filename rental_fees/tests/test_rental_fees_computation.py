from datetime import date, datetime

import pyexcel
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger

from odoo.addons.commown_devices.models.common import do_new_transfer, internal_picking
from odoo.addons.queue_job.tests.common import trap_jobs

from .common import RentalFeesTC


class RentalFeesComputationTC(RentalFeesTC):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        fees_product = cls.env["product.template"].create(
            {"name": "fees", "type": "service", "list_price": 0.0}
        )

        tax = cls.env["account.tax"].create(
            {
                "amount": 10.0,
                "amount_type": "percent",
                "price_include": False,
                "name": "Test tax",
                "type_tax_use": "sale",
            }
        )

        inv_model = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.po.partner_id.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": fees_product.product_variant_id.id,
                            "name": "Rental fees until ##DATE##",
                            "price_unit": 0.0,
                            "tax_ids": [(6, 0, tax.ids)],
                        },
                    )
                ],
            }
        )

        cls.fees_def.model_invoice_id = inv_model.id

        cls.expenses_journal = cls.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "TJ",
                "company_id": cls.env.company.id,
                "type": "bank",
            }
        )

        cls.env["account.payment.method"].create(
            {
                "name": "Electronic In",
                "code": "electronic",
                "payment_type": "inbound",
            }
        )

        cls.customer_journal = cls.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": cls.env.company.id,
                "type": "bank",
            }
        )

        repack_loc = cls.env.ref("commown_devices.stock_location_repackaged_devices")
        cls.repackaged_fp_loc = cls.env["stock.location"].create(
            {"name": "Repackaged FP", "location_id": repack_loc.id},
        )

    def compute(self, until_date, fees_def=None, run=True, invoice=False, sync=True):
        fees_def = fees_def or self.fees_def

        computation = self.env["rental_fees.computation"].create(
            {
                "fees_definition_ids": [(6, 0, fees_def.ids)],
                "until_date": until_date,
                "partner_id": self.env.ref("base.res_partner_1").id,
            }
        )
        if run:
            if sync:
                with trap_jobs() as trap:
                    computation.action_run()
                trap.perform_enqueued_jobs()
            else:
                computation.action_run()

        if invoice:
            computation.action_invoice()

        return computation

    def pay_invoice(self, invoice, journal):
        if invoice.state == "draft":
            invoice.action_post()
        register_payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": self.customer_journal.id})
        )
        register_payment._create_payments()
        self.assertEqual(invoice.payment_state, "paid")

    def pay_supplier_invoice(self, supplier_invoice):
        self.pay_invoice(supplier_invoice, self.expenses_journal)

    def test_open_job(self):
        comp = self.compute("2021-01-31", sync=False)

        self.assertEqual(comp.display_name, "Wood Corner (01/31/2021)")
        self.assertEqual(comp.state, "running")

        action1 = comp.button_open_job()
        self.assertEqual(action1["res_model"], "queue.job")
        job = self.env[action1["res_model"]].browse(action1["res_id"])

        action2 = job.open_related_action()
        self.assertEqual(action2["res_model"], "rental_fees.computation")
        self.assertEqual(comp, self.env[action2["res_model"]].browse(action2["res_id"]))

    def pay_customer_invoice(self, invoice):
        self.pay_invoice(invoice, self.customer_journal)

    def create_invoices_until(self, contract, until_date, pay=True):
        invoices = self.env["account.move"]
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

        device2 = contract2.lot_ids
        self.scrap_device(device2, date(2021, 4, 5))

        self.create_invoices_until(contract1, "2021-05-01")
        self.create_invoices_until(contract2, "2021-05-01")

        c1 = self.compute("2021-01-31", invoice=True)
        self.assertEqual(c1.fees, 0.0)
        self.assertIn("01/31/2021", c1.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c1.invoice_ids.amount_total, 0.0)

        c2 = self.compute("2021-02-28", invoice=True)
        self.assertEqual(c2.fees, 2.5)
        self.assertIn("02/28/2021", c2.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c2.invoice_ids.amount_total, 2.75)
        self.assertEqual(c2.invoice_ids.amount_tax, 0.25)

        action = c2.button_open_details()
        details = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(details, c2.detail_ids)

        c3 = self.compute("2021-03-31", invoice=True)
        self.assertEqual(c3.fees, 7.5)
        self.assertIn("03/31/2021", c3.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c3.invoice_ids.amount_total, 5.5)
        self.assertEqual(c3.invoice_ids.amount_tax, 0.5)

        c4 = self.compute("2021-04-30", invoice=True)
        self.assertEqual(c4.fees, 317.5)
        self.assertIn("04/30/2021", c4.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c4.invoice_ids.amount_total, 341.0)
        self.assertEqual(c4.invoice_ids.amount_tax, 31.0)
        compensations = c4.compensation_details()
        self.assertEqual(compensations.mapped("fees"), [300.0])

        # Paying an invoice, even after another one was emitted must work
        self.pay_supplier_invoice(c2.invoice_ids)
        self.assertEqual(c2.invoice_ids.payment_state, "paid")

        # Adding an invoice while a later computation exists must raise
        with self.assertRaises(ValidationError) as err:
            c2.invoice_ids |= c2.invoice_ids.copy()
        self.assertEqual(
            "Operation not allowed: there are later fees computations with"
            " invoices which amount would become invalid.",
            err.exception.args[0],
        )

        # Same with the action_invoice method
        with self.assertRaises(UserError) as err:
            c2.action_invoice()
        self.assertEqual(
            "There is a later invoice for the same fees definition",
            err.exception.args[0],
        )

        # Invoicing requires a model: check this too
        with self.env.cr.savepoint():
            self.fees_def.model_invoice_id = False
            with self.assertRaises(UserError) as err:
                self.compute("2021-05-30", invoice=True)
        self.assertEqual(
            "Please set the invoice model on all fees definitions.",
            err.exception.args[0],
        )

        # Generate an ods report
        file_content, file_type = self.env["ir.actions.report"]._render_py3o(
            "rental_fees.action_py3o_spreadsheet_fees_rental_computation", c4.ids
        )
        self.assertEqual(file_type, "ods")

        ods = pyexcel.get_book(file_content=file_content, file_type=file_type)
        self.assertEqual(
            ods.sheet_names(),
            [
                "Global figures",
                "Detailed rental fees",
                "Detailed compensations",
                "Per device revenues",
            ],
        )

        def _find_row_by_text(text, from_row=0):
            for row in range(from_row, len(s_sum)):
                if text in s_sum.row_at(row):
                    return row
            self.fail("Text %s not found after row %s" % (text, from_row))

        # Check the summary sheet:
        s_sum = ods.sheet_by_name("Global figures")

        # - Until date
        _find_row_by_text("Situation at date: 04/30/2021")

        # - Amounts per fees definition
        expected = {
            "Agreement": "Test fees_def",
            "Rental fees since the beginning": 17.5,
            "Compensation fees since the beginning": 300,
            "Already invoiced since the beginning": 7.5,
            "Fees to be invoiced": 310.0,
        }
        _row = _find_row_by_text("Agreement")
        self.assertEqual(
            dict(zip(s_sum.row_at(_row)[2:7], s_sum.row_at(_row + 1)[2:7])), expected
        )
        # - Amount totals
        expected["Agreement"] = "Totals"
        self.assertEqual(
            dict(zip(s_sum.row_at(_row)[2:7], s_sum.row_at(_row + 2)[2:7])), expected
        )

        # - Devices per fees def
        expected = {
            "Agreement": "Test fees_def",
            "Nb of devices under agreement": 3,
            "Nb of devices that generated fees": 1,
            "Nb of devices no longer operable": 1,
            "Nb of devices generating fees": 1,
        }
        _row = _find_row_by_text("Agreement", from_row=_row + 1)
        self.assertEqual(
            dict(zip(s_sum.row_at(_row)[2:7], s_sum.row_at(_row + 1)[2:7])), expected
        )
        # - Devices totals
        expected["Agreement"] = "Totals"
        self.assertEqual(
            dict(zip(s_sum.row_at(_row)[2:7], s_sum.row_at(_row + 2)[2:7])), expected
        )

        s_dev = ods.sheet_by_name("Per device revenues")
        product_col = [c for c in s_dev.column[3] if c != "" and type(c) == str]
        self.assertEqual(product_col, ["Product"] + 3 * ["Fairphone 3"])

    def test_send_report_for_invoicing(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        comp = self.compute("2022-03-01")
        comp.action_send_report_for_invoicing()

        self.assertEqual(comp.mapped("invoice_ids.state"), ["draft"])
        inv = comp.invoice_ids
        msg = inv.message_ids.filtered(lambda m: m.message_type == "notification")[0]
        self.assertEqual(
            msg.subject,
            "[%s] Fees to be invoices as of 03/01/2022" % self.env.company.name,
        )
        self.assertEqual(
            msg.attachment_ids.mapped("mimetype"),
            ["application/vnd.oasis.opendocument.spreadsheet"],
        )

    def test_action_reset_ok_and_error1(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        comp = self.compute("2022-03-01")

        self.assertTrue(comp.fees)

        comp.action_reset()
        self.assertFalse(comp.detail_ids)
        self.assertEqual(comp.state, "draft")
        self.assertFalse(comp.fees)

        with self.assertRaises(UserError) as err:
            comp.action_reset()
        self.assertEqual(
            err.exception.args[0],
            "Cannot reset fees computation if not in the 'done' state",
        )

    def test_action_reset_error2(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        comp = self.compute("2022-03-01")

        self.assertTrue(comp.fees)
        comp.action_send_report_for_invoicing()

        with self.assertRaises(UserError) as err:
            comp.action_reset()
        self.assertEqual(
            err.exception.args[0],
            "Cannot reset fees computation with a non-canceled invoice",
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
        merged_inv = self.env["account.move"].browse(list(invoices_info))
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
        with trap_jobs() as trap:
            contract.date_start = start_date
        trap.assert_jobs_count(
            1, only=contract.contract_line_ids._generate_forecast_periods
        )
        trap.perform_enqueued_jobs()
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
        self.assertIn(expected_msg, err.exception.args[0])

        with self.assertRaises(ValidationError) as err:
            partner_ref = "base.res_partner_1"
            self.fees_def.partner_id = self.env.ref(partner_ref).id
        self.assertIn(expected_msg, err.exception.args[0])

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
        contract.date_end = "2021-07-02"

        comp = self.compute("2022-02-01")
        self.assertFalse(comp.details("no_rental_compensation").mapped("fees"))

    def test_compute_no_rental_compensation_zero_3(self):
        "No rental conditions check: rented again before the limit"
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract1, "2021-02-01")
        contract1.date_start = "2021-02-01"
        self.receive_device("N/S 1", contract1, "2021-03-15")
        contract1.date_end = "2021-03-15"

        self.repackage_lot("N/S 1", "2021-03-16")

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 1", contract2, "2021-09-14")
        contract2.date_start = "2021-09-14"
        self.receive_device("N/S 1", contract2, "2021-09-14")
        contract2.date_end = "2021-09-14"

        comp = self.compute("2021-10-01")
        self.assertFalse(comp.details("no_rental_compensation").mapped("fees"))

    def repackage_lot(self, lot_name, date):
        lot = self.env["stock.lot"].search([("name", "=", lot_name)])
        orig = self.env.ref("commown_devices.stock_location_devices_to_check")
        dest = self.repackaged_fp_loc
        moves = internal_picking(lot, {}, None, orig, dest, False, date)
        picking = moves[0].picking_id
        do_new_transfer(picking, picking.scheduled_date)

    def test_compute_no_rental_compensation_non_zero_1(self):
        "No rental conditions fulfilled: compensation occurs, then no more fees"
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract1, "2021-02-01")
        contract1.date_start = "2021-02-01"
        while contract1.recurring_next_date <= date(2021, 4, 1):
            contract1._recurring_create_invoice()
        self.receive_device("N/S 1", contract1, "2021-04-01")
        contract1.date_end = "2021-04-01"

        self.repackage_lot("N/S 1", "2021-04-02")

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
        device = contract.lot_ids.ensure_one()
        while contract.recurring_next_date <= date(2021, 4, 1):
            contract._recurring_create_invoice()
        self.receive_device("N/S 1", contract, "2021-04-01")
        contract.date_end = "2021-04-01"

        self.scrap_device(device, date(2021, 12, 1))  # after no rental limit!

        comp = self.compute("2022-04-01")
        self.assertEqual(comp.compensation_details().mapped("fees"), [300.0])
        self.assertFalse(comp.rental_details().mapped("fees"))

    def _computation_with_excluded_device(self, **excluded_device_attrs):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        device = contract.lot_ids.ensure_one()
        while contract.recurring_next_date <= date(2021, 3, 1):
            contract._recurring_create_invoice()

        attrs = dict(
            {
                "fees_definition_id": self.fees_def.id,
                "device": device.id,
            },
            **excluded_device_attrs
        )
        self.env["rental_fees.excluded_device"].create(attrs)

        return self.compute("2022-03-01")

    def test_compute_excluded_device_with_compensation(self):
        comp = self._computation_with_excluded_device(
            with_compensation=True,
            reason="Used by an internal employee",
        )
        self.assertEqual(
            comp.details("excluded_device_compensation").mapped("fees"),
            [300.0],
        )

    def test_compute_excluded_device_without_compensation(self):
        comp = self._computation_with_excluded_device(
            with_compensation=False,
            reason="Returned to the supplier",
        )
        self.assertFalse(comp.details("excluded_device_compensation"))

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
        with mute_logger("odoo.addons.rental_fees.models.rental_fees_computation"):
            with self.assertRaises(RuntimeError) as err:
                self.compute("2021-05-01")

        # Check the generated error contains useful information
        exc = str(err.exception)
        self.assertIn("device: N/S 1", exc)
        self.assertIn(contract.name, exc)
        self.assertIn(self.fees_def.name, exc)

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
                    "to_date": date(2021, 4, 7),
                    "fees_def_line": self.fees_def.line_ids[0],
                    "is_forecast": False,
                },
                {
                    "contract": 1,
                    "from_date": date(2021, 4, 7),
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

    def test_split_periods_wrt_fees_def_error_no_line(self):
        fees_def = self.fees_def.copy({"name": "error_fees_def", "line_ids": False})
        compute = self.compute("2100-01-01", fees_def)

        with self.assertRaises(UserError) as exc:
            compute.split_periods_wrt_fees_def(fees_def, [])

        self.assertEqual(
            exc.exception.args[0],
            "Fees definition error_fees_def (id %d) has no line." % fees_def.id,
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
            err.exception.args[0],
            "Please use the same invoice model on all fees definition.",
        )

    def test_compute_with_fix_fees(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract, "2021-02-01")
        contract.date_start = "2021-02-01"
        self.create_invoices_until(contract, "2021-03-01")

        fees_line = self.fees_def.line_ids[0]
        fees_line.update({"fees_type": "fix", "monthly_fees": 0.4})

        comp = self.compute("2021-03-01")

        self.assertEqual(comp.fees, 0.8)  # 2 monthly invoices
        cur_symbol = self.env.company.currency_id.symbol
        self.assertEqual(fees_line.format_fees_amount(), "0.40 %s (fixed)" % cur_symbol)
