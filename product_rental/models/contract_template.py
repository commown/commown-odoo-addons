from odoo import api, fields, models


class ContractTemplate(models.Model):
    _inherit = "contract.template"

    contractual_documents = fields.Many2many(
        string="Contractual documents",
        comodel_name="ir.attachment",
        domain=[("public", "=", True), ("res_model", "=", False)],
    )

    commitment_period_number = fields.Integer(
        string="Commitment period number",
        help="Commitment duration in number of periods",
        default=0,
        required=True,
    )

    commitment_period_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("monthlylastday", "Month(s) last day"),
            ("quarterly", "Quarter(s)"),
            ("semesterly", "Semester(s)"),
            ("yearly", "Year(s)"),
        ],
        default="monthly",
        string="Commitment period type",
        required=True,
    )

    payment_mode_id = fields.Many2one(
        "account.payment.mode",
        string="Payment Mode",
        domain=[("payment_type", "=", "inbound")],
    )

    @api.multi
    def main_product_line(self):
        self.ensure_one()
        lines = self.contract_line_ids
        return (
            lines.filtered(lambda l: "##PRODUCT##" in l.name)
            or sorted(lines, key=lambda l: l.price_unit)
        )[0]
