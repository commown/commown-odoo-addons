from datetime import timedelta

from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ReconciliationWidgetTC(TransactionCase):
    def test_order_by_ascending_date(self):
        statement = self.env["account.bank.statement"].search([], limit=1).ensure_one()
        self.assertTrue(len(statement.line_ids) > 2)

        def st_line(widget_line):
            return self.env["account.bank.statement.line"].browse(
                widget_line["st_line"]["id"]
            )

        widget = self.env["account.reconciliation.widget"]
        lines_before = widget.get_bank_statement_data(statement.ids)["lines"]

        # Change last line's date to be the first in ascending order...
        new_date = min(st_line(line).date for line in lines_before) - timedelta(days=1)
        selected_line = st_line(lines_before[-1])
        selected_line.date = new_date

        # ... and it becomes the first
        lines_now = widget.get_bank_statement_data(statement.ids)["lines"]
        self.assertEqual(st_line(lines_now[0]), selected_line)
