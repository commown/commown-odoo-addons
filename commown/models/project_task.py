import logging

from odoo import fields, models

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone

_logger = logging.getLogger(__file__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    priority = fields.Selection(
        selection_add=[
            ("2", "High"),
        ],
    )

    show_internal_followup = fields.Boolean(
        "Show internal follow-up", related="project_id.show_internal_followup"
    )
    internal_followup = fields.Html(groups="base.group_user")

    def has_no_partner_message(self):
        "Return True if the author of one of task's messages is not an employee"
        self.ensure_one()
        employees = self.env.ref("base.group_user")
        for message in self.message_ids:
            author_groups = message.author_id.mapped("user_ids.groups_id")
            if author_groups and employees not in author_groups:
                return False
        return True

    def send_sms_reminder(self):
        self.ensure_one()

        country_code = self.partner_id.country_id.code
        phone = normalize_phone(self.partner_id.get_mobile_phone(), country_code)

        if phone and self.has_no_partner_message():
            # Send the SMS
            template = self.env.ref("commown.sms_template_issue_reminder")
            self.with_delay().message_post_send_sms_html(
                template, self.id, numbers=[phone], log_error=True
            )

        else:
            _logger.warning(
                "No SMS reminder sent to %s for task %s (id %d)",
                self.partner_id.name,
                self.name,
                self.id,
            )
