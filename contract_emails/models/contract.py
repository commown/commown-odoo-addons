import logging
from datetime import date

from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)


class ContractTemplatePlannedMailGenerator(models.Model):
    """Class that defines on a contract model what mail template to send
    and how to compute the planned send date from the contract start
    date.
    """
    _name = "contract_emails.planned_mail_generator"

    contract_id = fields.Many2one(
        "account.analytic.contract",
        string=u"Contract template",
        required=True,
        ondelete="cascade",
    )

    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email to send",
        required=True,
        domain="[('model', '=', 'account.analytic.account')]",
        ondelete="restrict",
    )

    interval_number = fields.Integer(
        default=0,
        string="Date interval number after contract start",
        help="In units defined below (Days/Week/Month/Year)",
    )

    interval_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("monthlylastday", "Month(s) last day"),
            ("yearly", "Year(s)"),
         ],
        default="monthly",
        string="Time unit",
        help=("Unit of the time interval after contract start date"
              " when the email will be sent"),
    )

    max_delay_days = fields.Integer(
        string="Max email delay (in days)",
        help=("Once this delay after the intended send date is expired,"
              " the email is not sent"),
        default=30,
    )

    send_date_offset_days = fields.Integer(
        string="Send date in days after contract start",
        compute="_compute_send_date_offset_days",
        store=True,
    )

    @api.depends("interval_type", "interval_number")
    def _compute_send_date_offset_days(self):
        today = date.today()
        for record in self:
            dt = self.env["account.analytic.account"].get_relative_delta(
                record.interval_type, record.interval_number)
            record.send_date_offset_days = (today + dt - today).days

    @api.model
    def cron_send_planned_mails(self):
        """ Mails to be sent today:
        - contract_start + related_offset >= today
        - not already sent
        """
        self.env.cr.execute("""
            SELECT C.id, PMG.id
              FROM account_analytic_account C
              JOIN account_analytic_contract CT ON (C.contract_template_id=CT.id)
              JOIN contract_emails_planned_mail_generator PMG ON (CT.id=PMG.contract_id)
             WHERE C.date_start + PMG.send_date_offset_days <= CURRENT_DATE
               AND CURRENT_DATE - PMG.max_delay_days < C.date_start + PMG.send_date_offset_days
               AND C.date_end IS NULL
               AND C.recurring_invoices
               AND NOT EXISTS(SELECT 1
                                FROM contract_emails_planned_mail_sent PMS
                               WHERE PMS.contract_id=C.id
                                 AND PMS.planned_mail_generator_id=PMG.id)
             ORDER BY C.id, PMG.send_date_offset_days
        """)
        result = self.env.cr.fetchall()
        channel = self.env.ref("contract_emails.channel")
        subtype = self.env.ref("mail.mt_comment")
        for contract_id, planned_mail_generator_id in result:
            contract = self.env["account.analytic.account"].browse(contract_id)
            pmg = self.env["contract_emails.planned_mail_generator"].browse(
                planned_mail_generator_id)
            pmg.send_planned_mail(contract)
            if not any(f.channel_id.id == channel.id
                       for f in contract.message_follower_ids):
                self.env['mail.followers'].create({
                    'channel_id': channel.id,
                    'partner_id': False,
                    'res_id': contract.id,
                    'res_model': contract._name,
                    'subtype_ids': [(6, 0, subtype.ids)]
                })

    @api.multi
    def send_planned_mail(self, contract):
        self.ensure_one()
        contract.message_post_with_template(self.mail_template_id.id)
        self.env["contract_emails.planned_mail_sent"].create({
            "send_date": fields.Datetime.now(),
            "contract_id": contract.id,
            "planned_mail_generator_id": self.id,
        })


class ContractTemplate(models.Model):
    _inherit = "account.analytic.contract"

    planned_mail_gen_ids = fields.One2many(
        string=u"Planned emails",
        comodel_name=u"contract_emails.planned_mail_generator",
        inverse_name='contract_id',
    )


class ContractSentPlannedEmail(models.Model):
    _name = "contract_emails.planned_mail_sent"
    _sql_constraints = [
        ('uniq_contract_and_mail_gen',
         'UNIQUE (contract_id, planned_mail_generator_id)',
         'Planned mail cannot be send twice for the same contract.'),
    ]

    contract_id = fields.Many2one(
        "account.analytic.account",
        String="Contract",
        required=True,
    )

    planned_mail_generator_id = fields.Many2one(
        "contract_emails.planned_mail_generator",
        String="Planned mail generator",
        required=True,
    )

    send_date = fields.Datetime(
        String="Date the planned email was sent",
        required=True,
    )
