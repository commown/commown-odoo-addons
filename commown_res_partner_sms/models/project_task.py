from odoo import models


class ProjectTask(models.Model):
    _inherit = "project.task"

    def send_sms_reminder(self):
        self.ensure_one()

        # Make sure the message is sent by the assigned user
        if self.user_id:
            self = self.sudo(self.user_id)

        phone = self.partner_id.get_mobile_phone()

        if phone and self.has_no_partner_message():
            # Send the SMS
            template = self.env.ref("commown.sms_template_issue_reminder")
            message = self.env["ir.fields.converter"].text_from_html(template.body_html)
            self.message_post_send_sms(message, numbers=[phone], log_error=True)

        else:
            _logger.warning(
                "No SMS reminder sent to %s for task %s (id %d)",
                self.partner_id.name,
                self.name,
                self.id,
            )
