from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class NetInstallerFeatureValueContractualChange(models.Model):
    _name = "commown_netinstaller.feature.value.contractual_change"
    _description = "Represents a change of a feature value at a date on a contract"

    contract_id = fields.Many2one(
        "contract.contract",
        required=True,
    )

    date = fields.Date(required=True, default=fields.Date.today)

    feature_value_id = fields.Many2one(
        "commown_netinstaller.feature.value",
        required=True,
    )

    @api.constrains("contract_id", "date", "feature_value_id")
    def _check_contract_date_feature(self):
        # Should not have more than one change of a given feature at a given date
        model = self.env["commown_netinstaller.feature.value.contractual_change"]
        domain = [
            ("id", "!=", self.id),
            ("contract_id", "=", self.contract_id.id),
            ("date", "=", self.date),
            ("feature_value_id.feature_id", "=", self.feature_value_id.feature_id.id),
        ]
        if model.search_count(domain) > 0:
            ctx = {
                "feat": self.feature_value_id.feature_id.name,
                "date": fields.Date.to_string(self.date),
            }
            raise ValidationError(
                _("More than one value change for %(feat)s at %(date)s." % ctx)
            )
