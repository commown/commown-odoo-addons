from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security

from odoo.addons.portal.controllers.web import Home as WebHome
from odoo.addons.web.controllers.utils import ensure_db, is_user_internal


class Home(WebHome):
    @http.route()
    def web_client(self, s_action=None, **kw):
        """
        We override this method, because the web_client controller methods
        in `web` and `portal` restrict access to the web section of the Odoo app
        if the current user is not internal.
        This blocks any portal users to access the Manager menus, located in the `web` section.

        So, we reimplemented the code, but added a allow_backend_passage method
        to allow certain portal users to access the web section of the Odoo app,
        depending on various conditions which can be defined in sub modules.

        This requires robust access rules to isolate correctly portal users
        from the rest of the app.
        """

        # Ensure we have both a database and a user
        ensure_db()
        if not request.session.uid:
            return request.redirect("/web/login", 303)

        session_user = request.env["res.users"].browse(request.session.uid)

        if kw.get("redirect"):
            return request.redirect(kw.get("redirect"), 303)
        if not security.check_session(request.session, request.env):
            raise http.SessionExpiredException("Session expired")
        if not session_user.has_group(
            "customer_manager_base.group_customer_admin"
        ) and not is_user_internal(request.session.uid):
            return request.redirect("/web/login_successful", 303)

        # Side-effect, refresh the session lifetime
        request.session.touch()

        # Restore the user on the environment, it was lost due to auth="none"
        request.update_env(user=request.session.uid)
        try:
            context = request.env["ir.http"].webclient_rendering_context()
            response = request.render("web.webclient_bootstrap", qcontext=context)
            response.headers["X-Frame-Options"] = "DENY"
            return response
        except AccessError:  # pragma: no cover
            return request.redirect("/web/login?error=access")
