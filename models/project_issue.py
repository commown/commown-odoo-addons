from odoo import models, fields


class ProjectIssue(models.Model):
    _inherit = "project.issue"

    lot_id = fields.Many2one(
        string=u"Involved device",
        help=u"Device involved in present issue",
        comodel_name="stock.production.lot",
        default=lambda self: self._default_lot_id(),
        domain=lambda self: self._domain_lot_id(),
    )

    def _contract(self):
        if not self.contract_id and "contract_id" in self.env.context:
            return self.env["account.analytic.account"].browse(
                self.env.context["contract_id"])
        else:
            return self.contract_id

    def _default_lot_id(self):
        "Returns the first lot_id found from contract quant_ids at present date"
        contract = self._contract()
        if contract:
            date = self.create_date or fields.Datetime.now()
            stock = contract.stock_at_date(date)
        else:
            stock = self.env["stock.production.lot"]
        return stock and stock[0]

    def _domain_lot_id(self):
        "Returns all the lots from the contract at the issue's creation date"
        contract = self._contract()
        if contract:
            date = self.create_date or fields.Datetime.now()
            return [("id", "in", contract.stock_at_date(date).ids)]
