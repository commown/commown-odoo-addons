# Copyright 2020-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import api, fields, models


class Project(models.Model):
    _inherit = "project.project"

    net_promoter_score = fields.Integer(
        compute="_compute_net_promoter_score", string="NPS", store=True, default=False
    )

    # Originally computed in _compute_rating_satisfaction_percentage,
    rating_count = fields.Integer(compute="_compute_net_promoter_score")

    @api.depends("rating_ids.rating")
    def _compute_net_promoter_score(self):
        for record in self:
            base_domain = [
                ("parent_res_model", "=", record._name),
                ("parent_res_id", "=", record.id),
                ("consumed", "=", True),
                (
                    "create_date",
                    ">=",
                    fields.Datetime.to_string(
                        fields.datetime.now() - timedelta(days=30)
                    ),
                ),
            ]
            ratings = self.env["rating.rating"].search(base_domain)
            record.rating_count = total_count = len(ratings)
            if not ratings:
                record.net_promoter_score = False
            else:
                promoters_count = len(ratings.filtered_domain([("rating", ">=", 9)]))
                detractors_count = len(ratings.filtered_domain([("rating", "<=", 6)]))
                record.net_promoter_score = int(
                    100 * (1.0 * promoters_count - detractors_count) / total_count
                )

    def _compute_rating_percentage_satisfaction(self):
        """
        This is an overload of the method written in rating/models/rating_parent_mixin.py.
        Since it uses a function with an assert instruction restricting rating scores
        between 0 and 5, which doesn't fit our NPS rating (ranging from 0 to 10),
        this leads to a AssertionError exception when computing affected fields.

        We don't use these fields, so we assign dummy values to them.
        """
        self.write(
            {
                "rating_percentage_satisfaction": -1,
                "rating_avg": -1,
                "rating_avg_percentage": -1,
            }
        )
