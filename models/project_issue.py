from odoo import models, fields, api


class ProjectIssue(models.Model):
    _inherit = 'project.issue'
    _order = 'priority desc, last_partner_msg_date asc'

    last_partner_msg_date = fields.Datetime(
        'Last partner message date',
        compute='_compute_last_partner_msg_date',
        store=True)

    @api.depends('date_action_last')
    def _compute_last_partner_msg_date(self):
        """By default, set the issue's creation date. If the partner has made
        at least one email or comment on the issue, the last one's
        date is used.
        """
        for record in self:
            date = record.last_partner_msg_date or record.create_date
            for msg in record.message_ids:
                if (msg.create_date > date and
                        msg.author_id == record.partner_id and
                        msg.message_type in ('email', 'comment')):
                    date = msg.create_date
            record.last_partner_msg_date = date
