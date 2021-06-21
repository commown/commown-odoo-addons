from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        """We do not want the sale order note to be copied to the invoice
        comment (pre-sale notes do generally not apply to invoices).
        We want to be able to add an invoice note (the "comment"
        attribute) however, so we do not remove it from the report but
        rather suppress the sale > invoice copy.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop('comment', None)
        return invoice_vals

    def _get_or_create_receivable_account(self, account_code):
        self.ensure_one()
        existing = self.env['account.account'].search([
            ('code', '=', account_code),
        ]).exists()
        if existing:
            account = existing[0]
        else:
            ref = self.env.ref
            account = self.env['account.account'].create({
                'code': account_code,
                'name': self.partner_id.name,
                'tag_ids': [(6, 0, [ref('account.account_tag_operating').id])],
                'user_type_id': ref('account.data_account_type_receivable').id,
                'tax_ids': [(6, 0, ref('l10n_fr.1_tva_normale').ids)],
                'reconcile': True,
            })
        return account

    @api.multi
    def action_confirm(self):
        """Add a dedicated receivable account to new customers. Use the ext_id
        in config parameter `commown.default_customer_receivable_tax`
        as a default tax for this account.
        """
        partner = self.partner_id.commercial_partner_id
        account_code = '411-C-%s' % partner.id
        account = partner.property_account_receivable_id
        if not account or account.code != account_code:
            new_account = self._get_or_create_receivable_account(account_code)
            partner.update({'property_account_receivable_id': new_account.id})

        return super(SaleOrder, self).action_confirm()

    def risk_analysis_lead_title(
            self, so_line, contract=None, secondary_index=None):
        title = super(SaleOrder, self).risk_analysis_lead_title(
            so_line, contract=contract, secondary_index=secondary_index)
        coupons = self.used_coupons()
        if coupons:
            title += (
                u' - COUPON: ' +
                u', '.join(coupons.mapped('campaign_id.name')))
        return title
