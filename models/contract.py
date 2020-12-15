import logging

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

    def generate_planned_mail_templates(self, contract):
        create = self.env['contract_emails.planned_mail_template'].create
        for gen in self:
            create({
                "mail_template_id": gen.mail_template_id.id,
                "planned_send_date": self.compute_send_date(contract),
                "res_id": contract.id,
            })


class ContractTemplate(models.Model):
    _inherit = "account.analytic.contract"

    planned_mail_gen_ids = fields.One2many(
        string=u"Planned emails",
        comodel_name=u"contract_emails.planned_mail_generator",
        inverse_name='contract_id'
    )

    @api.multi
    def generate_planned_mail_templates(self, domain=None):
        " Method that generates planned emails for all related contracts. "
        domain = domain or []

        c_model = self.env["account.analytic.account"]
        mgen_model = self.env["contract_emails.planned_mail_generator"]
        pmt_model = self.env["contract_emails.planned_mail_template"]

        for c_template in self:
            domain = domain + [("contract_template_id", "=", c_template.id)]
            contracts = c_model.search(domain)
            mgens = mgen_model.search([('contract_id', '=', c_template.id)])
            _logger.info(u"Generating %d planned mails of contract template %s",
                         len(contracts) * len(mgens), c_template.name)
            for contract in contracts:
                for mgen in mgens:
                    pmt_model.create({
                        "mail_template_id": mgen.mail_template_id.id,
                        "planned_send_date": mgen.compute_send_date(contract),
                        "res_id": contract.id,
                    })


class Contract(models.Model):
    _inherit = "account.analytic.account"

    def button_open_planned_emails(self):
        self.ensure_one()
        pmt_model = 'contract_emails.planned_mail_template'
        emails = self.env[pmt_model].search([
            ("res_id", "=", self.id),
            ("model_id.model", "=", self._name),
        ])
        result = {
            'type': 'ir.actions.act_window',
            'res_model': pmt_model,
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
