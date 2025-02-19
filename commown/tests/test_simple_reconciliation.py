from datetime import date

from odoo.tests.common import SavepointCase


class SimpleReconciliationTC(SavepointCase):
    def setUp(self):
        super().setUp()

        partner1 = self.env.ref("base.res_partner_address_15")
        partner2 = self.env.ref("base.res_partner_address_28")
        self.assertEqual(partner1.commercial_partner_id, partner2.commercial_partner_id)
        partner3 = self.env.ref("base.partner_demo_portal")

        self.account = self.env.ref("l10n_fr.1_pcg_5113")

        lines = [
            {
                "name": "Test aml 1",
                "partner_id": partner1.id,
                "account_id": self.account.id,
                "date_maturity": date(2018, 1, 1),
                "credit": 2,
                "debit": 0,
            },
            {
                "name": "Test aml 2",
                "partner_id": partner2.id,
                "account_id": self.account.id,
                "date_maturity": date(2018, 1, 10),
                "credit": 2,
                "debit": 0,
            },
            {
                "name": "Test aml 3",
                "partner_id": partner2.id,
                "account_id": self.account.id,
                "date_maturity": date(2018, 1, 11),
                "credit": 0,
                "debit": 2,
            },
            {
                "name": "Test aml 4",
                "partner_id": partner1.id,
                "account_id": self.account.id,
                "date_maturity": date(2018, 1, 21),
                "credit": 0,
                "debit": 2,
            },
            {
                "name": "Test aml 5",
                "partner_id": partner3.id,
                "account_id": self.account.id,
                "date_maturity": date(2018, 5, 1),
                "credit": 2,
                "debit": 0,
            },
        ]

        journal = self.env.ref("slimpay_statements_autoimport.slimpay_journal")
        self.move = self.env["account.move"].create(
            {"name": "My move", "journal_id": journal.id}
        )
        aml = self.env["account.move.line"].with_context(check_move_validity=False)
        for num, line in enumerate(lines):
            line["move_id"] = self.move.id
            aml.create(line)

    def reconcile(self, method):
        amr = self.env["account.mass.reconcile"].create(
            {"name": "Test with method %s" % method, "account": self.account.id}
        )
        meth = self.env["account.mass.reconcile.method"].create(
            {
                "name": method,
                "write_off": 0.0,
                "date_base_on": "newest",
                "task_id": amr.id,
                "journal_id": self.move.journal_id.id,
                "account_id": self.account.id,
            }
        )
        amr.run_reconcile()
        return amr.history_ids.reconcile_line_ids

    def assertReconcilesEqual(self, res, *expected_aml_name_pairs):
        actual_aml_name_pairs = tuple(
            r.mapped("reconciled_line_ids.name")
            for r in res.mapped("full_reconcile_id")
        )
        self.assertEqual(expected_aml_name_pairs, actual_aml_name_pairs)

    def test_without_max_reconcile_days_gap(self):
        self.assertReconcilesEqual(
            self.reconcile("mass.reconcile.simple.partner"),
            ["Test aml 1", "Test aml 4"],
            ["Test aml 2", "Test aml 3"],
        )

    def test_with_max_reconcile_days_gap(self):
        self.assertReconcilesEqual(
            self.reconcile("mass.reconcile.simple.partner_commown"),
            ["Test aml 2", "Test aml 3"],
        )
