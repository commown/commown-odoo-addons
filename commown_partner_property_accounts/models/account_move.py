from odoo import api, models


class PropertyAccountsAccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        "Automatically create a payable account for partners of Vendor Bills"
        purchase_move_types = self.get_purchase_types()
        ctx_move_type = self._context.get("default_move_type")
        seen_partners_ids = set()

        for vals in vals_list:
            partner_id = vals.get("partner_id")
            if not partner_id or partner_id in seen_partners_ids:
                continue

            if vals.get("move_type", ctx_move_type) in purchase_move_types:
                partner = self.env["res.partner"].browse(partner_id)
                partner._create_payable_account()
                seen_partners_ids.add(partner_id)

        return super().create(vals_list)

    def write(self, vals):
        "Automatically create a payable account for partners of Vendor Bills"
        new_partner_id = vals.get("partner_id")

        if new_partner_id:
            purchase_moves = self.filtered(lambda mv: mv.is_purchase_document())

            if purchase_moves:
                self.env["res.partner"].browse(new_partner_id)._create_payable_account()

        return super().write(vals)
