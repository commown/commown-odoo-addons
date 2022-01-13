from odoo import models, api, fields, _


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    contract_id = fields.Many2one(
        'account.analytic.account',
        string='Contract',
        default=lambda self: self._default_contract(),
        domain=lambda self: self._domain_contract(),
    )
    commercial_partner_id = fields.Many2one(
        'res.partner', related='partner_id.commercial_partner_id')
    require_contract = fields.Boolean(
        'Requires a contract',
        related='project_id.require_contract')

    def _default_contract(self):
        domain = self._domain_contract()
        if self.env["account.analytic.account"].search_count(domain) == 1:
            return self.env["account.analytic.account"].search(domain)

    def _domain_contract(self):
        domain = [("recurring_invoices", "=", True)]
        if self.partner_id:
            domain.append(("partner_id.commercial_partner_id", "=",
                           self.partner_id.commercial_partner_id.id))
        return domain

    @api.onchange("partner_id")
    def onchange_partner_id_set_contract(self):
        # Protect against onchange loop
        if (self.contract_id.partner_id.commercial_partner_id !=
                self.partner_id.commercial_partner_id):
            self.contract_id = self._default_contract() or False
        return {"domain": {"contract_id": self._domain_contract()}}

    @api.onchange("contract_id")
    def onchange_contract_id_set_partner(self):
        """ If partner was empty, use contract info to help setting it
        Also restrict to non-company partners.
        """
        domain = [("is_company", "=", False)]
        contract = self.contract_id
        if not self.partner_id and contract:
            domain.append(("commercial_partner_id", "=",
                           contract.partner_id.commercial_partner_id.id))
            if self.env["res.partner"].search_count(domain) == 1:
                self.partner_id = self.env["res.partner"].search(domain).id
        return {"domain": {"partner_id": domain}}
