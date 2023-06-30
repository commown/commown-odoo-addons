from odoo import models


class ProjectTask(models.Model):
    _inherit = "project.task"

    def urban_mine_send_mail(self, email_xmlid, coupon_campaign_xmlid, *attachments):
        if self.user_id and self.env.user != self.user_id:
            self = self.sudo(self.user_id)

        ref = lambda name: self.env.ref("urban_mine.%s" % name)

        if coupon_campaign_xmlid:
            campaign = ref(coupon_campaign_xmlid)
            coupon = self.env["coupon.coupon"].create({"campaign_id": campaign.id})
            self = self.with_context({"coupon": coupon.code})

        self.message_post_with_template(
            ref(email_xmlid).id,
            attachment_ids=[(4, att.id) for att in attachments],
        )

    def urban_mine_build_autoinvoice(
        self,
        tags,
        payment_term,
        description,
        report_name="urban_mine.report_autoinvoice",
    ):

        # Use task's user to perform all actions: invoice, payment, a.s.o.
        if self.user_id:
            self = self.sudo(self.user_id)

        ref = self.env.ref
        product = ref("urban_mine.product")
        invoice = self.env["account.invoice"].create(
            {
                "type": "in_invoice",
                "company_id": ref("base.main_company").id,
                "currency_id": ref("base.EUR").id,
                "reference": "COMMOWN-MU-%d" % self.id,
                "account_id": self.partner_id.property_account_payable_id.id,
                "payment_term_id": payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": description,
                            "account_id": product.property_account_expense_id.id,
                            "analytic_tag_ids": [(6, 0, tags.ids)] if tags else False,
                            "price_unit": product.standard_price,
                            "invoice_line_tax_ids": [
                                (6, 0, product.supplier_taxes_id.ids)
                            ],
                            "uom_id": ref("uom.product_uom_unit").id,
                        },
                    )
                ],
                "partner_id": self.partner_id.id,
            }
        )
        invoice.action_invoice_open()

        self.env["ir.actions.report"]._get_report_from_name(
            report_name
        ).ensure_one().render(invoice.ids)

        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", invoice._name),
                ("res_id", "=", invoice.id),
            ]
        )
