from odoo import models


class Contract(models.Model):
    _inherit = "contract.contract"

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
