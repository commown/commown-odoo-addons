import html

from odoo import _, api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _prepare_invoice(self):
        """We do not want the sale order note to be copied to the invoice
        comment (pre-sale notes do generally not apply to invoices).
        We want to be able to add an invoice note (the "comment"
        attribute) however, so we do not remove it from the report but
        rather suppress the sale > invoice copy.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop("comment", None)
        return invoice_vals

    def _get_or_create_receivable_account(self, account_code):
        self.ensure_one()
        existing = (
            self.env["account.account"]
            .search(
                [
                    ("code", "=", account_code),
                ]
            )
            .exists()
        )
        if existing:
            account = existing[0]
        else:
            ref = self.env.ref
            account = self.env["account.account"].create(
                {
                    "code": account_code,
                    "name": self.partner_id.name,
                    "tag_ids": [(6, 0, [ref("account.account_tag_operating").id])],
                    "user_type_id": ref("account.data_account_type_receivable").id,
                    "tax_ids": [(6, 0, ref("l10n_fr.1_tva_normale").ids)],
                    "reconcile": True,
                }
            )
        return account

    def _create_receivable_account(self):
        """Add a dedicated receivable account to new customers. Use the ext_id
        in config parameter `commown.default_customer_receivable_tax`
        as a default tax for this account.
        """
        partner = self.partner_id.commercial_partner_id
        account_code = "411-C-%s" % partner.id
        account = partner.property_account_receivable_id
        if not account or account.code != account_code:
            new_account = self._get_or_create_receivable_account(account_code)
            partner.update({"property_account_receivable_id": new_account.id})

    def _create_investment_followup_task(self):
        product_tmpl_ids = (
            self.env["product.template"]
            .search([("is_equity", "=", True), ("equity_type", "=", "invest")])
            .ids
        )

        line_tmpl = _(
            "<p><b>Sale number:</b> {sale_name}</p>"
            "<p><b>Sale date:</b> {date.year}-{date.month}-{date.day}</p>"
            "<p><b>Product:</b> {product_name}</p>"
        )

        description = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.id in product_tmpl_ids:
                description.append(
                    line_tmpl.format(
                        sale_name=html.escape(self.name),
                        date=self.date_order,
                        product_name=html.escape(line.product_id.display_name),
                    )
                )

        if description:
            ref = self.env.ref
            project = ref("commown.investment_followup_project")
            self.env["project.task"].create(
                {
                    "project_id": project.id,
                    "name": line.order_partner_id.name,
                    "user_id": project.user_id.id,
                    "partner_id": line.order_partner_id.id,
                    "stage_id": ref("commown.investment_followup_start_stage").id,
                    "description": "\n".join(description),
                }
            )

    def _add_buyer_to_support_group(self):
        for group in self.mapped(
            "order_line.product_id.product_tmpl_id.support_group_ids"
        ):
            group.add_users(self.partner_id.user_ids)

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        self._create_receivable_account()
        self._create_investment_followup_task()
        self._add_buyer_to_support_group()
        return super(SaleOrder, self).action_confirm()

    def risk_analysis_lead_title(self, so_line, contract=None, secondary_index=None):
        title = super(SaleOrder, self).risk_analysis_lead_title(
            so_line, contract=contract, secondary_index=secondary_index
        )
        coupons = self.used_coupons()
        if coupons:
            title += " - COUPON: " + ", ".join(coupons.mapped("campaign_id.name"))
        return title
