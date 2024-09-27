from datetime import date

from odoo import _, models
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    def urban_mine_name(self):
        return "COMMOWN-MU-%d" % self.id

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

    def urban_mine_create_po(self, price=0.0, invoice=False):
        """Create and return the purchase order of given storable at given price

        If invoice is passed, it is attached to the po.
        """
        storable_product = self.storable_product_id
        if not storable_product:
            raise UserError(_("Please fill-in the storable product field of the task!"))

        ptype = self.env.ref("urban_mine.picking_type_receive_to_diagnose")

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_id.id,
                "partner_ref": self.urban_mine_name(),
                "picking_type_id": ptype.id,
            }
        )

        po.order_line |= self.env["purchase.order.line"].create(
            {
                "name": storable_product.name,
                "product_id": storable_product.id,
                "product_qty": 1,
                "product_uom": storable_product.uom_id.id,
                "price_unit": price,
                "date_planned": date.today(),
                "order_id": po.id,
            }
        )

        if invoice:
            po.order_line.invoice_lines |= invoice.invoice_line_ids

        po.button_confirm()
        return po

    def urban_mine_build_autoinvoice(
        self,
        tags,
        payment_term,
        description,
        report_name="urban_mine.report_autoinvoice",
    ):

        ref = self.env.ref
        product = ref("urban_mine.product").product_variant_id

        price = product.standard_price  # purchase at the urban mine product price!

        invoice = self.env["account.invoice"].create(
            {
                "type": "in_invoice",
                "company_id": ref("base.main_company").id,
                "currency_id": ref("base.EUR").id,
                "reference": self.urban_mine_name(),
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
                            "price_unit": price,
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

        po = self.urban_mine_create_po(price, invoice)
        invoice.origin = po.name

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
