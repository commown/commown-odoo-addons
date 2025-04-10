from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"
    _order = "priority desc, last_partner_msg_date asc"

    last_partner_msg_date = fields.Datetime("Last partner message date")

    @api.model_create_multi
    def create(self, values_list):
        "Set last_partner_msg_date to utcnow by default"
        tasks = super().create(values_list)
        for task in tasks:
            if task.last_partner_msg_date is False:
                task.last_partner_msg_date = task.create_date
        return tasks

    def message_post(self, *args, **kwargs):
        """Update the last_partner_msg_date field when a message is posted.

        If the partner has made at least one email or comment on the task,
        the last one's date is used.
        """
        msg = super().message_post(*args, **kwargs)
        date = self.last_partner_msg_date or self.create_date
        if (
            msg.create_date > date
            and msg.author_id == self.partner_id
            and msg.message_type in ("email", "comment")
        ):
            self.sudo().last_partner_msg_date = msg.create_date
        return msg
