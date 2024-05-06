# Copyright 2023 Commown SCIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Contract(models.Model):

    _inherit = "contract.contract"

    @api.multi
    def action_show_contract_forecast(self):
        result = super().action_show_contract_forecast()
        result["view_mode"] = "graph,pivot,tree"
        graph_view = self.env.ref("commown_contract_forecast.forecast_view_graph")
        result["views"] = [(graph_view.id, "graph"), (None, "pivot"), (None, "tree")]
        return result
