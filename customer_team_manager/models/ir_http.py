from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        "Complete session info with `is_in_group_user` for use in js code (eg. widgets)"

        result = super().session_info()
        admin_group_ref = "customer_team_manager.group_customer_admin"
        result["is_customer_admin"] = self.env.user.has_group(admin_group_ref)
        return result
