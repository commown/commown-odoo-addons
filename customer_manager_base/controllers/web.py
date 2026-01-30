from odoo.http import request

from odoo.addons.commown_allow_backend_passage.controllers import web


class CustomerManagerBaseWeb(web.Home):
    def allow_backend_passage(self):
        session_user = request.env["res.users"].browse(request.session.uid)
        admin_grp = "customer_manager_base.group_customer_admin"

        return super().allow_backend_passage() or session_user.has_group(admin_grp)
