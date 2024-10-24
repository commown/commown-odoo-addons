from odoo.addons.product_rental.tests.test_website import WebsiteBaseTC


def clean_text(html_node):
    "Return the \n and multiple whitespaces cleaned-up text content of given node"
    return " ".join(html_node.text_content().split())


class PortalPaymentTemplatesTC(WebsiteBaseTC):
    """Test class for the payment of orders by portal users.

    There are two different situations, both tested here:

    1. the user is buying a product and wants to pay its basket
    2. commercial services asked the user to validate a prepared order; its state
       is then 'sent'.
    """

    def setUp(self):
        super().setUp()

        self.order = self.env.ref("sale.portal_sale_order_1")
        self.order.require_signature = False

        self.env["payment.token"].create(
            {
                "partner_id": self.order.partner_id.id,
                "acquirer_id": self.env.ref("payment.payment_acquirer_stripe").id,
                "acquirer_ref": "test-ref",
                "verified": True,
            }
        )

        # Necessary (but not sufficient) to make is_big_b2b True.
        # A last criterion is needed that can be set using the force_big_b2b method.
        b2b_website = self.env.ref("website_sale_b2b.b2b_website")
        self.order.partner_id.user_ids.update({"website_id": b2b_website.id})
        product = self.order.order_line[0].product_id
        ct = self.env.ref("product_rental.contract_tmpl_basic")
        product.property_contract_template_id = ct.id

    def setup_preconditions(self, big_b2b, authorized, sent):
        """Setup and check the given preconditions:

        - `big_b2b` forces the order's big B2B evaluation to given boolean
        - `authorized` forces the user's permission to make an order to given boolean
        """

        user = self.order.partner_id.user_ids[0]
        failed = "Prerequisite failed"

        if not authorized:
            # User is B2B but not in the dedicated group
            self.order.partner_id.parent_id = self.env.ref("base.res_partner_1").id
            _group_ref = "customer_manager_base.group_customer_purchase"
            self.assertFalse(user.has_group(_group_ref))
        self.assertIs(bool(authorized), user.is_authorized_to_order(), failed)

        set_param = self.env["ir.config_parameter"].set_param
        set_param("website_sale_b2b.big_b2b_min_qty", 0 if bool(big_b2b) else 10000)
        self.assertIs(bool(big_b2b), self.order.is_big_b2b(), failed)

        if not sent:
            self.order.action_cancel()
            self.order.action_draft()
        self.assertIs(bool(sent), self.order.state == "sent", failed)

    def render_payment(self, big_b2b, authorized, sent):
        "Setup the case and mimic the /shop/payment website_sale module controller"

        self.setup_preconditions(big_b2b, authorized, sent)

        render_values = dict(
            order=self.order,
            website_sale_order=self.order,
            errors=[],
            partner=self.order.partner_id.id,
            only_services=self.order.only_services,
            payment_action_id=self.env.ref("payment.action_payment_acquirer").id,
            return_url="/shop/payment/validate",
            bootstrap_formatting=True,
            access_token=self.order.access_token,
            tokens=self.order.partner_id.payment_token_ids,
        )

        return self.render_view(
            "website_sale_b2b.payment",
            sudo_as=self.order.partner_id.user_ids,
            **render_values
        )

    def render_order(self, big_b2b, authorized, sent):
        self.setup_preconditions(big_b2b, authorized, sent)

        order_sudo = self.order.sudo()
        payment_token = self.order.partner_id.payment_token_ids[0]
        render_values = {
            "sale_order": order_sudo,
            "token": "no matter",
            "return_url": "/shop/payment/validate",
            "bootstrap_formatting": True,
            "partner_id": order_sudo.partner_id.id,
            "report_type": "html",
            "res_company": order_sudo.company_id,
            "pms": payment_token,
            "acquirers": payment_token.acquirer_id,
        }

        return self.render_view(
            "sale.sale_order_portal_template",
            sudo_as=self.order.partner_id.user_ids,
            **render_values
        )

    def assertWarning(self, html_doc, true_false, warning, err_msg):
        nodes = html_doc.xpath("//*[hasclass('alert-warning')]")
        found = any(warning in clean_text(node) for node in nodes)
        err_msg += " found" if found else " not found"
        self.assertIs(bool(true_false), found, err_msg)

    def assertSubmitButton(self, html_doc, true_false, text):
        buttons = html_doc.xpath("//button[@type='submit']")
        found = any(text in clean_text(button) for button in buttons)
        err_msg = "Submit button entitled '%s'" % text
        err_msg += " found" if found else " not found"
        self.assertIs(bool(true_false), found, err_msg)

    def assertCommercialSubmitButton(self, html_doc, true_false):
        self.assertSubmitButton(html_doc, true_false, "Submit my request")

    def assertCommercialRequestMessage(self, html_doc, true_false):
        warning = "a member of our sales team will contact you"
        self.assertWarning(html_doc, true_false, warning, "Commercial request message")

    def assertUnauthorizedMessage(self, html_doc, true_false):
        warning = "You are not allowed to place an order"
        self.assertWarning(html_doc, true_false, warning, "Unauthorized message")

    def assertPayAndConfirmSubmitButton(self, html_doc, true_false):
        self.assertSubmitButton(html_doc, true_false, "Pay & Confirm")

    def test_render_payment_template_big_b2b_authorized(self):
        html_doc = self.render_payment(big_b2b=True, authorized=True, sent=True)

        self.assertCommercialSubmitButton(html_doc, True)
        self.assertCommercialRequestMessage(html_doc, True)
        self.assertUnauthorizedMessage(html_doc, False)
        self.assertPayAndConfirmSubmitButton(html_doc, False)

    def test_render_payment_template_big_b2b_not_authorized(self):
        html_doc = self.render_payment(big_b2b=True, authorized=False, sent=True)

        self.assertCommercialSubmitButton(html_doc, False)
        self.assertCommercialRequestMessage(html_doc, False)
        self.assertUnauthorizedMessage(html_doc, True)
        self.assertPayAndConfirmSubmitButton(html_doc, False)

    def test_render_payment_template_not_big_b2b_not_authorized(self):
        html_doc = self.render_payment(big_b2b=False, authorized=False, sent=True)

        self.assertCommercialSubmitButton(html_doc, False)
        self.assertCommercialRequestMessage(html_doc, False)
        self.assertUnauthorizedMessage(html_doc, True)
        self.assertPayAndConfirmSubmitButton(html_doc, False)

    def test_render_order_template_big_b2b_authorized_sent(self):
        html_doc = self.render_order(big_b2b=True, authorized=True, sent=True)

        self.assertCommercialSubmitButton(html_doc, False)
        self.assertCommercialRequestMessage(html_doc, False)
        self.assertUnauthorizedMessage(html_doc, False)
        self.assertPayAndConfirmSubmitButton(html_doc, True)

    def test_render_order_template_big_b2b_not_authorized_sent(self):
        """Even if not authorized, the user as received a link with the order's access
        token, so it may be unauthenticated but should be able to validate the order.
        In this case, the Pay & Confirm button must thus be present.
        """

        html_doc = self.render_order(big_b2b=True, authorized=False, sent=True)

        self.assertCommercialSubmitButton(html_doc, False)
        self.assertCommercialRequestMessage(html_doc, False)
        self.assertUnauthorizedMessage(html_doc, False)
        self.assertPayAndConfirmSubmitButton(html_doc, True)
