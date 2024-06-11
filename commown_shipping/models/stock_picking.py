import datetime

from dateutil import relativedelta

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _cron_count_late_lot_pickings(self):
        fil = self.env.ref("commown_shipping.late_pickings_with_lots_filter")
        filter_domain = safe_eval(
            fil.domain,
            {"datetime": datetime, "relativedelta": relativedelta.relativedelta},
        )
        late_pickings = self.env["stock.picking"].search_count(filter_domain)
        if late_pickings > 0:
            channel = self.env.ref("commown_shipping.late_pickings_with_lots_channel")
            template = self.env.ref("commown_shipping.late_pickings_with_lots_mail")
            channel.with_context(
                {"late_pickings": late_pickings}
            ).message_post_with_template(template.id)
