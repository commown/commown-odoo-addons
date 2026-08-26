from odoo import fields, models


class Contract(models.Model):
    _inherit = "contract.contract"

    netinstaller_feature_value_change_ids = fields.One2many(
        string="Netinstaller feature value changes",
        comodel_name="commown_netinstaller.feature.value.contractual_change",
        inverse_name="contract_id",
    )

    def _netinstaller_feature_values(self, date=None):
        self.ensure_one()

        if date is None:
            date = fields.Date.context_today(self)

        # Feature values:

        # - from product
        product = self.get_main_rental_line().sale_order_line_id.product_id
        value_by_feature = {
            v.feature_id: v for v in product.cumulated_netinstaller_feature_value_ids
        }

        # - from contractual changes
        changes = {}
        for change in self.netinstaller_feature_value_change_ids.filtered(
            lambda c: c.date <= date
        ):
            feature = change.feature_value_id.feature_id
            changes.setdefault(feature, [])
            changes[feature].append(change)

        for feature, _changes in changes.items():
            value_by_feature[feature] = max(
                _changes, key=lambda c: c.date
            ).feature_value_id

        result = self.env["commown_netinstaller.feature.value"]
        for feature_value in value_by_feature.values():
            result |= feature_value

        return result

    def netinstaller_specs(self, date=None):
        self.ensure_one()

        feature_values = self._netinstaller_feature_values(date)
        result = {fv.feature_id.name: fv.typed_value() for fv in feature_values}

        # Post install scripts:
        result["post_install_script"] = [
            {
                "git_clone_url": script.git_clone_url,
                "git_branch_name": script.git_branch_name,
                "cmd": script.cmd,
            }
            for script in self.partner_id.netinstaller_post_install_scripts()
        ]

        return result
