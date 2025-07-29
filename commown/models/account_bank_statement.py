from odoo import models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    def reconciliation_widget_preprocess(self):
        "Override to order statement lines by date instead of by id."
        result = super().reconciliation_widget_preprocess()
        result["st_lines_ids"] = (
            self.env["account.bank.statement.line"]
            .browse(result["st_lines_ids"])
            .sorted("date")
            .ids
        )
        return result
