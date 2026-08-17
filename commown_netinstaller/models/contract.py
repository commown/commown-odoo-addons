from odoo import fields, models


class Contract(models.Model):
    _inherit = "contract.contract"

    netinstaller_feature_value_change_ids = fields.One2many(
        string="Netinstaller feature value changes",
        comodel_name="commown_netinstaller.feature.value.contractual_change",
        inverse_name="contract_id",
    )

    def netinstaller_specs(self):
        self.ensure_one()

        # Feature values:
        product = self.get_main_rental_line().sale_order_line_id.product_id
        result = product.netinstaller_feature_typed_values()

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
