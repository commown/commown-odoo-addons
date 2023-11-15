from odoo import models
from odoo.http import request

from odoo.addons.portal.controllers.portal import _build_url_w_params


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _handle_exception(cls, exc):
        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(
                _build_url_w_params(redirect.url_to, request.params), code=redirect.type
            )

        return super(IrHttp, cls)._handle_exception(exc)
