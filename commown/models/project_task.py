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
