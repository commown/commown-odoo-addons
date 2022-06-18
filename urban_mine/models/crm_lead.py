from odoo import api, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def urban_mine_send_label(self, label_name):
        # Send the message as the user of the lead
        if self.user_id:
            self = self.sudo(self.user_id)

        label = self.parcel_labels(label_name, force_single=True)
        email_template = self.env.ref("urban_mine.email_template_with_label")

        self.message_post_with_template(
            email_template.id, attachment_ids=[(4, label.id)],
        )

    def urban_mine_payment(self, campaign, product, journal, tags, description,
                           report_name="urban_mine.report_autoinvoice"):

        # Use lead's user to perform all actions: invoice, payment, a.s.o.
        if self.user_id:
            self = self.sudo(self.user_id)

        ref = self.env.ref
        invoice = self.env["account.invoice"].create({
            "type": u"in_invoice",
            "company_id": ref("base.main_company").id,
            "currency_id": ref("base.EUR").id,
            "reference": "COMMOWN-MU-%d" % self.id,
            "account_id": self.partner_id.property_account_payable_id.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": product.id,
                "name": description,
                "account_id": product.property_account_expense_id.id,
                "analytic_tag_ids": [(6, 0, tags.ids)] if tags else False,
                "price_unit": product.standard_price,
                "invoice_line_tax_ids": [(6, 0, product.supplier_taxes_id.ids)],
                "uom_id": ref("uom.product_uom_unit").id,
            })],
            "partner_id": self.partner_id.id,
        })
        invoice.action_invoice_open()

        if journal:
            method = ref("account.account_payment_method_manual_out")
            payment = self.env["account.payment"].create({
                "partner_id": invoice.partner_id.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "invoice_ids": [(6, 0, invoice.ids)],
                "journal_id": journal.id,
                "amount": invoice.residual,
                "payment_method_id": method.id,
            })
            payment.post()

        self.env["ir.actions.report"]._get_report_from_name(
            report_name).ensure_one().render(invoice.ids)

        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", invoice._name),
            ("res_id", "=", invoice.id),
        ])

        email_template = ref("urban_mine.email_template_with_auto_invoice")
        coupon = self.env["coupon.coupon"].create({"campaign_id": campaign.id})

        self.with_context({"coupon": coupon.code}).message_post_with_template(
            email_template.id,
            attachment_ids=[(4, att.id) for att in attachments],
        )
