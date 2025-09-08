import hashlib
import json

from odoo import models
from odoo.http import request
from odoo.tools import ustr


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        """Complete session info with :
        - `is_customer_admin` for use in js code (eg. widgets)
        - `load_menus` which allows a customer admin user to load the Odoo backend menus
          when accessing the /web side of the Odoo app.
          (this is necessary because portal users are filtered out
          in super().session_info())
        """

        user = self.env.user

        result = super().session_info()
        result["is_customer"] = not self.env.user.has_group("base.group_user")

        if result["is_customer"]:
            menus = (
                self.env["ir.ui.menu"]
                .with_context(lang=request.session.context["lang"])
                .load_menus(request.session.debug)
            )
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(
                ordered_menus, default=ustr, sort_keys=True
            ).encode()

            result["cache_hashes"].update(
                {
                    "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[
                        :64
                    ],  # sha512/256
                }
            )
            result.update(
                {
                    # current_company should be default_company
                    "user_companies": {
                        "current_company": user.company_id.id,
                        "allowed_companies": {
                            comp.id: {
                                "id": comp.id,
                                "name": comp.name,
                                "sequence": comp.sequence,
                            }
                            for comp in user.company_ids
                        },
                    },
                    "show_effect": True,
                    "display_switch_company_menu": user.has_group(
                        "base.group_multi_company"
                    )
                    and len(user.company_ids) > 1,
                }
            )

        return result
