from base64 import b64encode
from pathlib import Path

from odoo.tests.common import TransactionCase
from odoo.tools.float_utils import float_is_zero

HERE = (Path(__file__) / "..").resolve()


class AccountJournalTC(TransactionCase):
    def setUp(self):
        super().setUp()

        fname = "reporting_sample.csv"
        with open(HERE / fname, "rb") as fobj:
            csv_content = fobj.read()

        journal = self.env.ref("account_move_slimpay_import.slimpay_journal")
        account_receivable = self.env["account.account"].create(
            {
                "code": "TEST.RECE",
                "name": "Test receivable",
                "user_type_id": self.env.ref("account.data_account_type_liquidity").id,
            }
        )
        journal.receivable_account_id = account_receivable

        self.importer = self.env["credit.statement.import"].create(
            {
                "journal_id": journal.id,
                "input_statement": b64encode(csv_content),
                "file_name": fname,
                "partner_id": journal.partner_id.id,
                "receivable_account_id": journal.receivable_account_id.id,
                "commission_account_id": journal.commission_account_id.id,
            }
        )

    def test(self):
        action = self.importer.import_statement()

        imported_move = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(imported_move.state, "draft")
        self.assertEqual(imported_move.amount, 85)
        self.assertEqual(len(imported_move.line_ids), 7)
        self.assertTrue(
            float_is_zero(
                sum(imported_move.line_ids.mapped("balance")),
                precision_digits=imported_move.currency_id.decimal_places,
            )
        )
