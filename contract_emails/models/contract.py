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

    def compute_send_date(self, contract):
        self.ensure_one()
        return (fields.Date.from_string(contract.date_start)
                + contract.get_relative_delta(
                    self.interval_type, self.interval_number))

    def generate_planned_mail_templates(self, contract, before, after):
        """ Generate planned mails for given contract, which send date is
        strictly before the `before` date and after or equal to the `after`
        date.
        """
        if not contract.date_start:
            return
        create = self.env['contract_emails.planned_mail_template'].create
        for gen in self:
            planned_send_date = gen.compute_send_date(contract)
            if before is not None and planned_send_date >= before:
                continue
            if after is not None and planned_send_date <= after:
                continue
            create({
                "mail_template_id": gen.mail_template_id.id,
                "planned_send_date": planned_send_date,
                "res_id": contract.id,
            })


class ContractTemplate(models.Model):
    _inherit = "account.analytic.contract"

    planned_mail_gen_ids = fields.One2many(
        string=u"Planned emails",
        comodel_name=u"contract_emails.planned_mail_generator",
        inverse_name='contract_id',
    )


class Contract(models.Model):
    _name = "account.analytic.account"
    _inherit = [
        "account.analytic.account",
        "contract_emails.planned_mail_template_object",
    ]

    def planned_email_generators(self):
        return self.mapped('contract_template_id.planned_mail_gen_ids')

    @api.model
    def create(self, values):
        values.pop('planned_mail_gen_ids', None)  # XXX
        contract = super(Contract, self).create(values)
        contract._generate_planned_emails()
        return contract

    @api.multi
    def write(self, values):
        old_date_end = self.date_end
        res = super(Contract, self).write(values)
        if "date_start" in values or "contract_template_id" in values:
            for contract in self:
                contract._generate_planned_emails(unlink_first=True)
        if "date_end" in values:
            if not values["date_end"]:
                # date_end is unset: regenerate emails after old end date
                after = fields.Date.from_string(old_date_end)
                for contract in self:
                    contract._generate_planned_emails(after=after)
            else:
                if not old_date_end or values["date_end"] < old_date_end:
                    # date_end is set from unset or set sooner: remove planned
                    # emails to be sent after the new end date
                    for contract in self:
                        for pmt in contract._get_planned_emails():
                            if pmt.planned_send_date >= values["date_end"]:
                                pmt.sudo().unlink()
                else:
                    # date_end is set later: regenerate planned emails between
                    # the old and new end dates
                    for contract in self:
                        before = fields.Date.from_string(values["date_end"])
                        after = fields.Date.from_string(old_date_end)
                        contract._generate_planned_emails(
                            before=before, after=after)
        return res
