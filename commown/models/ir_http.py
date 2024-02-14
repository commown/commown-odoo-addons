from odoo import models
from odoo.http import request

from odoo.addons.portal.controllers.portal import _build_url_w_params


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _handle_exception(cls, exc):
        request.website = request.env["website"].get_current_website()
        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(
                _build_url_w_params(redirect.url_to, request.params), code=redirect.type
            )

        return super(IrHttp, cls)._handle_exception(exc)

    def session_info(self):
        "Complete session info with is_in_group_user info"
        result = super().session_info()
        group_user = self.env.ref("base.group_user")
        result["is_in_group_user"] = group_user in self.env.user.groups_id
        return result
