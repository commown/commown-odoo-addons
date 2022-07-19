import logging

from odoo import fields, models

_logger = logging.getLogger(__file__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    priority = fields.Selection(
        selection_add=[
            ("2", "High"),
        ],
    )

    def slimpay_payment_issue_process_automatically(self):
        """Handle a payment issue automatically only when it comes from a
        contract generated invoice.
        """
        self.ensure_one()
        return bool(self.invoice_id.mapped("invoice_line_ids.contract_line_id"))

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

        # Make sure the message is sent by the assigned user
        if self.user_id:
            self = self.sudo(self.user_id)

        phone = self.partner_id.mobile or self.partner_id.phone

        if phone and self.has_no_partner_message():
            # Temporarily remove followers
            _data = [f.copy_data()[0] for f in self.message_follower_ids]
            self.sudo().message_follower_ids.unlink()

            # Send the SMS
            template = self.env.ref("commown.sms_template_issue_reminder")
            layout = "commown_payment_slimpay_issue.message_nowrap_template"
            self.with_context(custom_layout=layout).message_post_with_template(
                template.id, message_type="comment"
            )

            # Put followers back
            current_followers = self.mapped("message_follower_ids.partner_id")
            for data in _data:
                if data["partner_id"] not in current_followers.ids:
                    self.env["mail.followers"].create(data)
        else:
            _logger.warning(
                "No SMS reminder sent to %s for task %s (id %d)",
                self.partner_id.name,
                self.name,
                self.id,
            )
