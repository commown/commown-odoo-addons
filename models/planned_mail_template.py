from odoo import api, fields, models


class PlannedMailTemplate(models.Model):
    """Class that defines a mail template that will be evaluated and sent
    at a given date in the future, and store when it was effectively sent.
    """
    _name = "contract_emails.planned_mail_template"

    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email to send",
        required=True,
    )

    planned_send_date = fields.Date(
        string="Planned send date",
        required=True,
    )

    effective_send_time = fields.Datetime(
        string="Effective send date and time",
    )

    res_id = fields.Integer(
        "Related Document ID",
        index=True,
        help="Id of the mail origin resource",
    )

    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        related="mail_template_id.model_id",
        help="The type of document this template can be used with",
    )

    document = fields.Char(
        'Document',
        compute='_compute_document',
        readonly=True,
        store=False,
    )

    @api.depends('model_id', 'res_id')
    def _compute_document(self):
        for pmt in self:
            pmt.document = "%s,%s" % (pmt.model_id.model, pmt.res_id)

    @api.model
    def cron_send_planned_mails(self):
        planned_mails = self.env[self._name].search([
            ("effective_send_time", "=", False),
            ("planned_send_date", "<=", fields.Datetime.now()),
        ])
        for planned_mail in planned_mails:
            src_obj = self.env[planned_mail.model_id.model].browse(
                planned_mail.res_id)
            planned_mail.send_planned_mail(src_obj)

    @api.multi
    def send_planned_mail(self, src_obj):
        """Post planned mail from given mail.thread instance `src_obj`."""
        self.ensure_one()
        src_obj.message_post_with_template(self.mail_template_id.id)
        self.effective_send_time = fields.Datetime.now()
