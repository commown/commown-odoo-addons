from .common import SlimpayControllersTC


class SlimpayPaymentControllersTC(SlimpayControllersTC):
    def test_slimpay_portal_sale_ok_simple(self):
        """Perform a portal sale, paid using a mocked Slimpay and using a fake
        feedback.
        """
        # A portal user adds a product in its cart and clicks the "Buy" button
        self.authenticate("portal", "portal")
        self.add_product_to_user_cart()
        tx_ref = self.pay_cart()

        self.check_transaction(tx_ref, "draft")
        self.simulate_feedback(tx_ref)
        tx = self.check_transaction(tx_ref, "done")

        self.assertEqual("•••• IBAN my-iban (my-bank)", tx["token_id"][1])
        self.assertEqual(1, len(tx["sale_order_ids"]))
        self.check_so(tx["sale_order_ids"][0], "sale")

    def test_slimpay_portal_sale_ok_with_two_transaction(self):
        """Perform a successful portal sale in two steps:
        - first transaction fails (typically times out while user finds its
        bank coordinates)
        - second transaction succeeds.
        """
        self.authenticate("portal", "portal")
        self.add_product_to_user_cart()

        tx1_ref = self.pay_cart()
        self.check_transaction(tx1_ref, "draft")
        self.simulate_feedback(tx1_ref, "closed.aborted.aborted_byclient")
        tx1 = self.check_transaction(tx1_ref, "cancel")
        self.assertFalse(tx1["sale_order_ids"])

        tx2_ref = self.pay_cart()
        self.check_transaction(tx2_ref, "draft")
        self.simulate_feedback(tx2_ref)
        tx2 = self.check_transaction(tx2_ref, "done")
        self.assertEqual(1, len(tx2["sale_order_ids"]))
        self.check_so(tx2["sale_order_ids"][0], "sale")
        # Check transactions' reference start with the same SO name
        self.assertEqual(1, len({tx["reference"].split("-")[0] for tx in (tx1, tx2)}))

    def test_feedback_error(self):
        """In case of an error, feedback response in a 200 with a message

        This 200 (=normal) response is to avoid useless multiple postings from Slimpay.
        """
        self.authenticate("portal", "portal")
        resp = self.simulate_feedback("non-existing-ref", assert_code=200)
        self.assertEqual(resp, "Incorrect transaction reference")
