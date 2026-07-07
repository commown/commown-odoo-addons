from odoo import Command
from odoo.tests import TransactionCase


class SponsoringTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env.ref("base.partner_demo_portal")

    @classmethod
    def create_contract(cls, partner, date_start=False):
        cline_attrs = {
            "name": "Line 1",
            "specific_price": 1.0,
            "quantity": 1.0,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "product_id": cls.env.ref("product.product_product_1").id,
        }

        return cls.env["contract.contract"].create(
            {
                "name": "Dummy contract",
                "partner_id": partner.id,
                "date_start": date_start,
                "contract_line_ids": [Command.create(cline_attrs)],
            }
        )
