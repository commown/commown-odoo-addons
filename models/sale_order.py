from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        self.create_risk_analysis_leads()
        return result

    def risk_analysis_lead_title(self, ctx):
        return u'[%(sale)s-%(count)02d] %(descr)s' % ctx

    def create_risk_analysis_leads(self):
        ctx = {'sale': self.name, 'count': 0}

        for so_line in self.order_line:
            product = so_line.product_id

            team = product.followup_sales_team_id
            if not team:
                continue

            stages = self.env['crm.stage'].search(
                [('team_id', '=', team.id)], order='sequence')
            stage_id = stages[0].id if stages else False
            for stage in stages:
                if '[stage: start]' in stage.name:
                    stage_id = stage.id
                    break

            ctx['descr'] = product.display_name

            for _num in range(int(so_line.product_uom_qty)):
                ctx['count'] += 1
                lead = self.env['crm.lead'].create({
                    'name': self.risk_analysis_lead_title(ctx),
                    'partner_id': self.partner_id.id,
                    'type': 'opportunity',
                    'team_id': team.id,
                    'stage_id': stage_id,
                    'so_line_id': so_line.id,
                    })
                # Override post-create behaviour that auto-assigns team_id
                data = {'team_id': team.id}
                if ctx['count'] == 1:
                    # shortcut from first opportunity to the sale
                    # (cannot have more than 1 opportunity related
                    #  to a single sale)
                    data['order_ids'] = [(6, 0, self.ids)]
                lead.update(data)
