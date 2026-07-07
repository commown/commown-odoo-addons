from datetime import date, timedelta

from odoo import models

DEFAULT_DELTA_WEEKS_CONTRACT_START = 6


class SponsoringContract(models.Model):
    _inherit = "contract.contract"

    def write(self, values):
        "Create sponsors on newly started contracts"
        res = super().write(values)

        if "date_start" in values:
            param_delta_length = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "commown_sponsoring.delta_weeks_contract_start",
                    DEFAULT_DELTA_WEEKS_CONTRACT_START,
                )
            )
            for contract in self:
                if contract.date_start < date.today() + timedelta(
                    weeks=param_delta_length
                ):
                    contract.partner_id._create_sponsor_campaign()

        return res
