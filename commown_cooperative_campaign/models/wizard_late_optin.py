from datetime import date

from odoo import api, fields, models

from .discount import coop_ws_optin


class LateOptinWizard(models.TransientModel):
    _name = "coupon.late.optin.wizard"
    _description = "Helper to manually register a coupon"

    coupon_id = fields.Many2one(
        "coupon.coupon",
        string="Coupon",
        required=True,
    )

    date = fields.Date(
        string="Optin date",
        default=date.today(),
        required=True,
    )

    contract_id = fields.Many2one(
        string="Contract",
    )

    @api.onchange("coupon_id")
    def _onchange_coupon_id(self):
        so = self.coupon_id.used_for_sale_id
        if so:
            contracts = self.env["contract.contract"].search(
                [("contract_line_ids.sale_order_line_id.order_id", "=", so.id)],
            )
            if len(contracts) == 1:
                self.contract_id = contracts.id
            return {"domain": {"contract_id": [("id", "in", contracts.ids)]}}

    @api.multi
    def late_optin(self):

        partner, key = self.coupon_id._action_coop_prerequisites()
        campaign = self.coupon_id.campaign_id

        base_url = self.env["ir.config_parameter"].get_param(
            "commown_cooperative_campaign.base_url"
        )

        coop_ws_optin(
            base_url,
            campaign.name,
            key,
            self.contract_id.name,
            self.date,
            partner.tz,
            silent_double_optin=False,
        )
