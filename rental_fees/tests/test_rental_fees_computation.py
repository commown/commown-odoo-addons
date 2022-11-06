from datetime import date

from odoo.exceptions import ValidationError

from .common import RentalFeesTC


class RentalFeesComputationTC(RentalFeesTC):
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
        computation = self.env["rental_fees.computation"].create(
            {
                "fees_definition_id": (fees_def or self.fees_def).id,
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
        task = self.env["project.task"].create(
            {
                "name": "test breakage",
                "contractual_issue_type": "breakage",
                "contractual_issue_date": date(2021, 4, 5),
                "lot_id": device2.id,
                "contract_id": contract2.id,
            }
        )

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
        self.assertEqual(c4.fees, 420.0)
        self.assertIn("04/30/2021", c4.invoice_ids.invoice_line_ids[0].name)
        self.assertEqual(c4.invoice_ids.amount_total, 412.5)
        c4.invoice_ids.action_invoice_open()

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

    def test_cannot_modify_def_with_computation(self):
        "Cannot modify a fees def which has a non-draft computation"

        # Can modify while computation is draft:
        computation = self.compute("2021-02-01", run=False)
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

        computation._run()
        self.assertEqual(computation.state, "done")

        with self.assertRaises(ValidationError) as err:
            self.fees_def.line_ids |= self.env["rental_fees.definition_line"].create(
                {
                    "fees_definition_id": self.fees_def.id,
                    "sequence": 30,
                    "duration_value": 10,
                    "duration_unit": "months",
                    "fees_type": "proportional",
                    "monthly_fees": 0.4,
                }
            )
        self.assertIn(
            "Some non-draft computations use this fees definition.", err.exception.name
        )

        with self.assertRaises(ValidationError) as err:
            new_fees_def_line.duration_value = 20
        self.assertIn(
            "Some non-draft computations use this fees definition.", err.exception.name
        )
