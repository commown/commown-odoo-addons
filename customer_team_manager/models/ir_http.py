from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        "Complete session info with `is_in_group_user` for use in js code (eg. widgets)"

        result = super().session_info()
        result["is_customer"] = not self.env.user.has_group("base.group_user")
        return result
