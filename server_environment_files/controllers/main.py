# Copyright (C) 2019 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Modified by Commown


from werkzeug.utils import redirect

from odoo import http
from odoo.http import Controller
from odoo.tools.config import config


class ServerEnvironmentController(Controller):
    @http.route(
        "/server_environment_files" "/static/RUNNING_ENV/<local_path>",
        type="http",
        auth="public",
    )
    def environment_redirect(self, local_path, **kw):
        # Note: module_extension is present to make working
        # the module in normal configuration, with the folder
        # server_environment_files and in demo configuration, with the
        # module  server_environment_files_sample
        running_env = config.get("running_env", "default")
        new_path = "/server_environment_files/static/%s/%s" % (
            running_env,
            local_path,
        )
        return redirect(new_path, 303)
