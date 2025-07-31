from odoo.addons.account_invoice_merge_auto_pay.tests.common import inject_payment_data
from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC


class ContractRelatedPaymentTokenUniquifyTC(PaymentTokenUniquifyTC):
    @classmethod
    def setUpClass(cls):
        """Setup test data: two partners of self.company_s1 have a token
        and a contract using it:

          * first token is the main one of the contract's partner
          * second token is directly linked to the contract
        """
        super().setUpClass()
        inject_payment_data(cls, cls.company_s1_w1)

        token1 = cls.new_payment_token(cls.company_s1_w1)
        cls.contract1 = cls.new_contract(cls.company_s1_w1)
        cls.company_s1_w1.payment_token_id = token1.id

        token2 = cls.new_payment_token(cls.company_s1_w2, set_as_partner_token=False)
        cls.contract2 = cls.new_contract(cls.company_s1_w2)
        cls.contract2.payment_token_id = token2.id

    @classmethod
    def new_contract(cls, partner):
        product = cls.env.ref("product.product_product_1")
        return cls.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": partner.id,
                "invoice_partner_id": partner.id,
                "pricelist_id": partner.property_product_pricelist.id,
                "contract_type": "sale",
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Services from #START# to #END#",
                            "quantity": 1,
                            "uom_id": product.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2018-02-15",
                            "recurring_next_date": "2018-02-15",
                        },
                    )
                ],
            }
        )
