from odoo import api, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    @api.multi
    def reconciliation_widget_preprocess(self):
        "Override to order statement lines by date instead of by id."
        result = super(AccountBankStatement, self).reconciliation_widget_preprocess()
        result["st_lines_ids"] = (
            self.env["account.bank.statement.line"]
            .browse(result["st_lines_ids"])
            .sorted("date")
            .ids
        )
        return result
