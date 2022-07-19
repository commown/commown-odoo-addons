from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    contract_id = fields.Many2one(
        'contract.contract',
        string='Contract',
        default=lambda self: self._default_contract(),
        domain="[('partner_id.commercial_partner_id', '=', commercial_partner_id)]",
    )
    commercial_partner_id = fields.Many2one(
        'res.partner', related='partner_id.commercial_partner_id')
    contractual_issue_type = fields.Selection(
        [('loss', 'Loss'), ('breakage', 'Breakage'), ('theft', 'Theft')],
        string='Issue type',
    )
    contractual_issue_date = fields.Date(
        'Issue date',
        help='Date when the contractual issue occurred')
    penalty_exemption = fields.Boolean(
        'Penalty exemption', help='E.g.: customer paid, commercial initiative',
        default=False)
    contractual_issues_tracking = fields.Boolean(
        'Used for contractual issue tracking',
        related='project_id.contractual_issues_tracking')
    require_contract = fields.Boolean(
        'Requires a contract',
        related='project_id.require_contract')

    def _default_contract(self):
        if self.commercial_partner_id:
            domain = [('partner_id.commercial_partner_id', '=',
                       self.commercial_partner_id.id)]
            if self.env["contract.contract"].search_count(domain) == 1:
                return self.env["contract.contract"].search(domain)

    @api.onchange("partner_id")
    def onchange_partner_id_set_contract(self):
        # Protect against onchange loop
        if (self.contract_id.partner_id.commercial_partner_id !=
                self.partner_id.commercial_partner_id):
            self.contract_id = self._default_contract() or False

    @api.onchange("contract_id")
    def onchange_contract_id_set_partner(self):
        """ If partner was empty, use contract info to help setting it
        Also restrict to non-company partners.
        """
        if not self.partner_id and self.contract_id:
            domain = [
                ("is_company", "=", False),
                ("commercial_partner_id", "=",
                 self.contract_id.partner_id.commercial_partner_id.id),
            ]
            if self.env["res.partner"].search_count(domain) == 1:
                self.partner_id = self.env["res.partner"].search(domain).id
