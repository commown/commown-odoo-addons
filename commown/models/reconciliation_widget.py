from odoo import api, models


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    def _reconcile_line_date(self, line):
        st_line_id = line["st_line"]["id"]
        return self.env["account.bank.statement.line"].browse(st_line_id).date

    @api.model
    def get_bank_statement_data(self, bank_statement_ids):
        " Order lines to reconcile in ascending date order "
        result = super().get_bank_statement_data(bank_statement_ids)
        result["lines"] = sorted(result["lines"], key=self._reconcile_line_date)
        return result
