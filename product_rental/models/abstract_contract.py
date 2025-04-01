from odoo import fields, models


class ContractAbstractContract(models.AbstractModel):
    _inherit = "contract.abstract.contract"

    stock_ownership = fields.Selection(
        [("internal", "Rental"), ("customer", "Sale with service")],
        default="internal",
        required=True,
    )
