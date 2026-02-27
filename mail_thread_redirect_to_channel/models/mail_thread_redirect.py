from odoo import fields, models
from odoo.tools import safe_eval


class MailThreadRedirect(models.Model):
    _name = "mail.thread.redirect"

    name = fields.Char(required=True)

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("is_mail_thread", "=", True)],
    )

    model_name = fields.Char(related="model_id.model", readonly=True)

    target_channel_id = fields.Many2one(
        "mail.channel",
        required=True,
        domain=[("channel_type", "in", ("group", "channel"))],
    )

    filter_domain = fields.Char(string="Apply on")

    only_portal_users = fields.Boolean(
        string="Redirect only portal user messages",
        help="Only redirect messages from portal users (ie. non-employees)",
    )

    def _get_eval_domain(self):
        eval_context = {
            "datetime": safe_eval.datetime,
            "context_today": safe_eval.datetime.datetime.now,
        }
        return safe_eval.safe_eval(self.filter_domain or "[]", eval_context)
