# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models


class Project(models.Model):

    _inherit = "project.project"

    net_promoter_score = fields.Integer(
        compute="_compute_net_promoter_score", string="NPS",
        store=True, default=False)

    @api.one
    @api.depends('issue_ids.rating_ids.rating')
    def _compute_net_promoter_score(self):
        base_domain = [
            ('res_model', '=', self.issue_ids._name),
            ('res_id', 'in', self.issue_ids.ids),
            ('create_date', '>=', fields.Datetime.to_string(
                fields.datetime.now() - timedelta(days=30))),
        ]
        total_count = self.env['rating.rating'].search_count(base_domain)
        if total_count == 0:
            self.net_promoter_score = False
        else:
            promoters_count = self.env['rating.rating'].search_count(
                base_domain + [('rating', '>=', 9)])
            detractors_count = self.env['rating.rating'].search_count(
                base_domain + [('rating', '<=', 6)])
            self.net_promoter_score = int(
                100 * (1. * promoters_count - detractors_count) / total_count)
