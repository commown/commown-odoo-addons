from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC


class ContractRelatedPaymentTokenUniquifyTC(PaymentTokenUniquifyTC):
    def setUp(self):
        """Setup test data: two partners of self.company_s1 have a token
        and a contract using it:

          * first token is the main one of the contract's partner
          * second token is directly linked to the contract
        """
        super().setUp()

        token1 = self.new_payment_token(self.company_s1_w1)
        self.contract1 = self.new_contract(self.company_s1_w1)
        self.company_s1_w1.payment_token_id = token1.id

        token2 = self.new_payment_token(self.company_s1_w2, set_as_partner_token=False)
        self.contract2 = self.new_contract(self.company_s1_w2)
        self.contract2.payment_token_id = token2.id

    def new_contract(self, partner):
        product = self.env.ref("product.product_product_1")
        return self.env["contract.contract"].create(
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
