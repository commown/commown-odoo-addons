from odoo import api, models, fields


class UrbanMinePartner(models.Model):
    _inherit = 'res.partner'

    from_urban_mine = fields.Boolean("From urban mine registration",
                                     website_form_blacklisted=False)

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        result = super().create(vals)

        if vals.get("from_urban_mine", False):

            lead = self.env['crm.lead'].create({
                'name': result.name + ' - ' + result.city,
                'partner_id': result.id,
                'type': 'opportunity',
                'stage_id': self.env.ref('urban_mine.stage1').id,
            })

            # Override post-create behaviour that auto-assigns team_id
            lead.update({
                'team_id': self.env.ref('urban_mine.urban_mine_managers').id,
                'name': (u'[COMMOWN-MU-%d] ' % lead.id) + lead.name,
            })

        return result
