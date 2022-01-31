from datetime import date
from odoo import api, fields, models, _


class PlannedMailTemplate(models.Model):
    """Class that defines a mail template that will be evaluated and sent
    at a given date in the future, and store when it was effectively sent.
    """
    _name = "contract_emails.planned_mail_template"
    _order = 'planned_send_date asc, effective_send_time desc'

    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email to send",
        required=True,
        ondelete="cascade",
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

    def name_get(self):
        result = []
        for record in self:
            name = None
            if record.mail_template_id and record.model_id and record.res_id:
                try:
                    name = u' - '.join((record.get_object().display_name,
                                        record.mail_template_id.display_name))
                except:  # noqa
                    pass
            if name is None:
                _id, name = super(PlannedMailTemplate, record).name_get()[0]
            result.append((record.id, name))
        return result

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
        for pmail in planned_mails:
            pmail.get_object().planned_mail_send(pmail)

    @api.multi
    def get_object(self):
        self.ensure_one()
        return self.env[self.model_id.model].browse(self.res_id)


class PlannedMailTemplateObject(models.AbstractModel):
    _name = "contract_emails.planned_mail_template_object"

    def planned_email_generators(self):
        " This method is to be overloaded "
        raise NotImplementedError()

    def planned_mail_send(self, planned_mail):
        " Post planned mail with given mail template "
        self.ensure_one()
        self.message_post_with_template(planned_mail.mail_template_id.id)
        planned_mail.effective_send_time = fields.Datetime.now()

    def _generate_planned_emails(self, unlink_first=False, before=None,
                                 after=None):
        if after is None:
            after = date.today()
        self.ensure_one()
        if unlink_first:
            self._get_planned_emails().sudo().unlink()
        self.planned_email_generators().generate_planned_mail_templates(
            self, before=before, after=after)

    def _get_planned_emails(self):
        return self.env['contract_emails.planned_mail_template'].search([
            ("res_id", "in", self.ids),
            ("model_id.model", "=", self._name),
        ])

    def button_open_planned_emails(self):
        self.ensure_one()
        emails = self._get_planned_emails()
        result = {
            'type': 'ir.actions.act_window',
            'res_model': 'contract_emails.planned_mail_template',
            'domain': [('id', 'in', emails.ids)],
            'name': _('Planned emails'),
        }
        if len(emails) == 1:  # single sale: display it directly
            views = [(False, 'form')]
            result['res_id'] = emails.id
        else:  # display a list
            views = [(False, 'list'), (False, 'form')]
        result['views'] = views
        return result

    @api.multi
    def unlink(self):
        "Cascade delete related planned emails"
        self._get_planned_emails().sudo().unlink()
        super(PlannedMailTemplateObject, self).unlink()
