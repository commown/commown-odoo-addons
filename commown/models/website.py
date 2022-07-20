from odoo import api, models, tools
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    @api.multi
    def get_languages(self):
        self.ensure_one()
        if not request.env.user.has_group("website.group_website_publisher"):
            return self._get_languages()
        else:
            return [(lg.code, lg.name) for lg in self.language_ids]

    @tools.cache("self.id")
    def _get_languages(self):
        return [
            (lg.code, lg.name) for lg in self.language_ids.filtered("website_published")
        ]
