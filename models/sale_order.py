from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        self.create_risk_analysis_leads()
        return result

    def choose_stage(self, team):
        stages = self.env['crm.stage'].search(
            [('team_id', '=', team.id)], order='sequence')
        stage = stages[0] if stages else False
        for _stage in stages:
            if '[stage: start]' in _stage.name:
                stage = _stage
                break
        return stage

    def related_contracts(self):
        return self.env['account.analytic.account'].search([
            ('recurring_invoice_line_ids.sale_order_line_id.order_id',
             '=',
             self.id),
        ])

    def _create_lead(self, name, team, so_line, **kwargs):
        data = {
            'name': name,
            'partner_id': self.partner_id.id,
            'type': 'opportunity',
            'team_id': team.id,
            'stage_id': self.choose_stage(team),
            'so_line_id': so_line.id,
        }
        data.update(kwargs)
        lead = self.env['crm.lead'].create(data)
        # Override post-create behaviour that auto-assigns team_id
        lead.update({'team_id': team.id})
        return lead

    def risk_analysis_lead_title(self, so_line, contract=None):
        name = u'%s-00' % self.name if contract is None else contract.name
        return u'[%s] %s' % (name, so_line.product_id.display_name)

    def create_risk_analysis_leads(self):
        leads = self.env['crm.lead']

        # Create a RA lead for each contract line with a contract product
        # that has a followup team (as of today, should create 1 per contract)
        for contract in self.related_contracts():
            for _line in contract.recurring_invoice_line_ids:
                so_line = _line.sale_order_line_id
                product = so_line.product_id
                team = product.followup_sales_team_id
                if not team:
                    continue
                name = self.risk_analysis_lead_title(so_line, contract)
                leads |= self._create_lead(name, team, so_line,
                                           contract_id=contract.id)

        # Also create a lead for non contract products with a followup team
        for so_line in self.order_line:
            product = so_line.product_id
            team = product.followup_sales_team_id
            if team and not product.is_contract:
                name = self.risk_analysis_lead_title(so_line)
                leads |= self._create_lead(name, team, so_line)

        return leads
