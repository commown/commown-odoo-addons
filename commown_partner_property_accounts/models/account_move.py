from odoo import api, models


class PropertyAccountsAccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        "Automatically create a payable account for partners of Vendor Bills"
        seen_partners_ids = set()
        purchase_move_types = self.get_purchase_types()
        ctx_is_purchase = self._context.get("default_move_type") in purchase_move_types

        for vals in vals_list:
            if (
                (vals.get("move_type") in purchase_move_types or ctx_is_purchase)
                and vals.get("partner_id")
                and vals.get("partner_id") not in seen_partners_ids
            ):
                partner_id = vals.get("partner_id")
                partner = self.env["res.partner"].browse(partner_id).exists()
                partner._create_payable_account()

                seen_partners_ids.add(partner_id)

        return super().create(vals_list)

    def write(self, vals):
        "Automatically create a payable account for partners of Vendor Bills"
        if vals.get("partner_id") and (
            (
                self.is_purchase_document()
                and vals.get("move_type") not in self.get_sale_types()
            )
            or vals.get("move_type") in self.get_purchase_types()
        ):
            partner = self.env["res.partner"].browse(vals.get("partner_id")).exists()
            partner._create_payable_account()

            # Instruction fetched from the onchange method _inverse_partner_id,
            # to assign the newly created account to the payment_term lines.
            # (see odoo/addons/account/models/account_move_line.py:L1125)
            self.line_ids._conditional_add_to_compute(
                "account_id", lambda line: (line.display_type == "payment_term")
            )

        return super().write(vals)
