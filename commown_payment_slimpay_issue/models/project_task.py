import logging

from odoo import api, models

_logger = logging.getLogger(__file__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.onchange("stage_id")
    def send_sms_payment_issue(self):
        warn_partner_stage = self.env.ref(
            "payment_slimpay_issue.stage_warn_partner_and_wait"
        )
        if self.stage_id == warn_partner_stage:

            phone = record.partner_id.mobile or record.partner_id.phone
            if phone:
                template = env.ref("commown_payment_slimpay_issue.smspro_payment_issue")
                message = self.env["ir.fields.converter"].text_from_html(
                    template.body_html
                )
                self.message_post_send_sms(message, numbers=[phone], log_error=True)

            else:
                _logger.warning(
                    "Could not send SMS to %s (id %s): no phone number found"
                    % (record.partner_id.name, record.partner_id.id)
                )
