from datetime import date

from odoo.exceptions import ValidationError

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
            computation._run()

        if invoice:
            computation.action_invoice()

        return computation

    def pay(self, supplier_invoice):
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
                "invoice_ids": [(6, 0, [supplier_invoice.id])],
            }
        ).post()

    def test_compute_and_invoicing(self):
        contract1 = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract1, date="2021-02-15")
        contract1.date_start = "2021-02-15"

        contract2 = self.env["contract.contract"].of_sale(self.so)[1]
        self.send_device("N/S 2", contract=contract2, date="2021-03-06")
        contract2.date_start = "2021-03-06"

        device2 = contract2.quant_ids.lot_id
        self.scrap_device(device2, date(2021, 4, 5))

        while contract1.recurring_next_date <= date(2021, 5, 1):
            contract1._recurring_create_invoice()

        while contract2.recurring_next_date <= date(2021, 5, 1):
            contract2._recurring_create_invoice()

        c1 = self.compute("2021-01-31", invoice=True)
        self.assertEqual(c1.fees, 0.0)
        self.assertIn("01/31/2021", c1.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c1.invoice_ids.amount_total, 0.0)
        c1.invoice_ids.action_invoice_open()

        c2 = self.compute("2021-02-28", invoice=True)
        self.assertEqual(c2.fees, 2.5)
        self.assertIn("02/28/2021", c2.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c2.invoice_ids.amount_total, 2.5)
        c2.invoice_ids.action_invoice_open()

        c3 = self.compute("2021-03-31", invoice=True)
        self.assertEqual(c3.fees, 7.5)
        self.assertIn("03/31/2021", c3.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c3.invoice_ids.amount_total, 5.0)
        c3.invoice_ids.action_invoice_open()

        c4 = self.compute("2021-04-30", invoice=True)
        self.assertEqual(c4.fees, 320.0)
        self.assertIn("04/30/2021", c4.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c4.invoice_ids.amount_total, 312.5)
        c4.invoice_ids.action_invoice_open()
        compensations = c4.compensation_details()
        self.assertEqual(compensations.mapped("fees"), [300.0])

        # Paying an invoice, even after another one was emitted must work
        self.pay(c2.invoice_ids)
        self.assertEqual(c2.invoice_ids.state, "paid")

        # Adding an invoice while a later computation exists must raise
        with self.assertRaises(ValidationError) as err:
            c2.invoice_ids |= c2.invoice_ids.copy()
        self.assertEqual(
            "Operation not allowed: there are later fees computations with"
            " invoices which amount would become invalid.",
            err.exception.name,
        )

    def test_cannot_modify_important_def_fields_with_computation(self):
        "Cannot modify a fees def which has a non-draft computation"

        contract = self.env["contract.contract"].of_sale(self.so)[0]
        self.send_device("N/S 1", contract=contract, date="2021-02-15")
        contract.date_start = "2021-02-15"
        contract._recurring_create_invoice()

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

        # Modifications are restricted once computation is done:
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
        "No rental conditions fulfilled: compensation occurs then no other compensation"

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
        self.assertEqual(comp.details("no_rental_compensation").mapped("fees"), [300.0])
        self.assertFalse(comp.details("lost_device_compensation").mapped("fees"))
        self.assertFalse(comp.rental_details().mapped("fees"))

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
        _d = date

        periods = [
            {"from_date": _d(2021, 1, 10), "to_date": _d(2021, 2, 15), "contract": 0},
            {"from_date": _d(2021, 3, 15), "to_date": _d(2021, 4, 15), "contract": 1},
        ]

        self.assertEqual(
            [
                {
                    "contract": 0,
                    "from_date": _d(2021, 1, 10),
                    "to_date": _d(2021, 2, 15),
                    "fees_def_line": self.fees_def.line_ids[0],
                },
                {
                    "contract": 1,
                    "from_date": _d(2021, 3, 15),
                    "to_date": _d(2021, 4, 15),
                    "fees_def_line": self.fees_def.line_ids[1],
                },
            ],
            self.compute("2100-01-01").split_periods_wrt_fees_def(
                self.fees_def, periods
            ),
        )

    def test_split_periods_wrt_fees_def_2(self):
        _d = date

        periods = [
            {"from_date": _d(2021, 1, 10), "to_date": _d(2021, 6, 30), "contract": 0},
            {"from_date": _d(2021, 7, 15), "to_date": _d(2021, 12, 5), "contract": 1},
        ]

        self.assertEqual(
            [
                {
                    "contract": 0,
                    "from_date": _d(2021, 1, 10),
                    "to_date": _d(2021, 3, 10),
                    "fees_def_line": self.fees_def.line_ids[0],
                },
                {
                    "contract": 0,
                    "from_date": _d(2021, 3, 10),
                    "to_date": _d(2021, 6, 10),
                    "fees_def_line": self.fees_def.line_ids[1],
                },
                {
                    "contract": 0,
                    "from_date": _d(2021, 6, 10),
                    "to_date": _d(2021, 6, 30),
                    "fees_def_line": self.fees_def.line_ids[2],
                },
                {
                    "contract": 1,
                    "from_date": _d(2021, 7, 15),
                    "to_date": _d(2021, 12, 5),
                    "fees_def_line": self.fees_def.line_ids[2],
                },
            ],
            self.compute("2100-01-01").split_periods_wrt_fees_def(
                self.fees_def, periods
            ),
        )
