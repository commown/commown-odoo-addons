from datetime import date

from odoo.tests import tagged

from odoo.addons.account.tests.common import TestAccountReconciliationCommon


@tagged("-at_install", "post_install")
class SimpleReconciliationTC(TestAccountReconciliationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        partner1 = cls.env.ref("base.res_partner_address_15")
        partner2 = cls.env.ref("base.res_partner_address_28")
        assert partner1.commercial_partner_id == partner2.commercial_partner_id
        partner3 = cls.env.ref("base.partner_demo_portal")

        cls.account = cls.account_rcv

        cls.inv1 = cls.create_invoice(
            **{
                "partner_id": partner1.id,
                "date_invoice": date(2018, 1, 1),
                "invoice_amount": 2,
            }
        )

        cls.inv2 = cls.create_invoice(
            **{
                "partner_id": partner2.id,
                "date_invoice": date(2018, 1, 10),
                "invoice_amount": 2,
            }
        )

        cls.payment1 = cls.create_payment(
            **{
                "partner_id": partner2.commercial_partner_id.id,
                "account_id": cls.account.id,
                "date": date(2018, 1, 11),
                "amount": 2,
            }
        )

        cls.payment2 = cls.create_payment(
            **{
                "partner_id": partner1.commercial_partner_id.id,
                "account_id": cls.account.id,
                "date": date(2018, 1, 21),
                "amount": 2,
            },
        )

        cls.inv3 = cls.create_invoice(
            **{
                "partner_id": partner3.id,
                "date_invoice": date(2018, 5, 1),
                "invoice_amount": 2,
            }
        )

    @classmethod
    def create_invoice(cls, **params):
        "Helper that eases invoice move creation"
        invoice = cls._create_invoice(cls, **params)
        invoice.invoice_date_due = invoice.invoice_date
        invoice.action_post()
        return invoice

    @classmethod
    def create_payment(cls, **params):
        "Helper that eases payment move creation"
        params.update(
            {
                "partner_type": "customer",
                "payment_type": "inbound",
                "destination_account_id": params.pop("account_id"),
                "journal_id": cls.company_data["default_journal_bank"].id,
            }
        )
        payment = cls.env["account.payment"].create(params)
        payment.action_post()
        return payment

    def reconcile(self, method):
        journal = self.company_data["default_journal_sale"]

        amr = self.env["account.mass.reconcile"].create(
            {"name": "Test with method %s" % method, "account": self.account.id}
        )
        self.env["account.mass.reconcile.method"].create(
            {
                "name": method,
                "write_off": 0.0,
                "date_base_on": "newest",
                "task_id": amr.id,
                "journal_id": journal.id,
            }
        )
        amr.run_reconcile()
        return amr.history_ids.reconcile_line_ids

    def assertReconcilesEqual(self, res, *expected_aml_name_pairs):
        def smallest_id(rset):
            return rset.ids

        actual_aml_name_pairs = tuple(
            r.mapped("reconciled_line_ids") for r in res.mapped("full_reconcile_id")
        )
        self.assertEqual(
            sorted(expected_aml_name_pairs, key=smallest_id),
            sorted(actual_aml_name_pairs, key=smallest_id),
        )

    def test_without_max_reconcile_days_gap(self):
        self.assertReconcilesEqual(
            self.reconcile("mass.reconcile.simple.partner"),
            self.inv1.line_ids[1] | self.payment1.move_id.line_ids[1],
            self.inv2.line_ids[1] | self.payment2.move_id.line_ids[1],
        )

    def test_with_max_reconcile_days_gap(self):
        self.assertReconcilesEqual(
            self.reconcile("mass.reconcile.simple.partner_commown"),
            self.inv2.line_ids[1] | self.payment1.move_id.line_ids[1],
        )
