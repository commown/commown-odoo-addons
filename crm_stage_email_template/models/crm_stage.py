from odoo import fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain=[("model", "=", "crm.lead")],
        help=(
            "If set an email will be sent to the partner"
            "when the lead reaches this step."
        ),
    )
