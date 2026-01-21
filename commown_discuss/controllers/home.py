from odoo.http import request

from odoo.addons.commown_allow_backend_passage.controllers import web


class CommownHome(web.Home):
    def allow_backend_passage(self):
        "Allow backend passage to users subscribed to mail channels"
        session_user = request.env["res.users"].browse(request.session.uid)

        return (
            super().allow_backend_passage()
            or session_user.sudo().partner_id.channel_ids
        )
