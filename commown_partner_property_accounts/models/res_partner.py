from odoo import Command, api, models

_PROPERTY_ACCOUNT_DATA = {
    "payable": {
        "account_type": "liability_payable",
        "field_name": "property_account_payable_id",
        "code_template": "401.F.%d",
    },
    "receivable": {
        "account_type": "asset_receivable",
        "field_name": "property_account_receivable_id",
        "code_template": "411.C.%d",
    },
}


class CommownPartner(models.Model):
    _inherit = "res.partner"

    def _create_property_account(self, property_name):
        """If partner's payable or receivable account does not exist or
        is the fr standard one, create a dedicated account for the partner.
        The account is associated to the commercial_partner, if any, but
        linked to both partners.
        """
        assert property_name in ("payable", "receivable")

        data = _PROPERTY_ACCOUNT_DATA[property_name]
        ref_account = self.env["ir.property"]._get(data["field_name"], "res.partner")

        for partner in self:
            partner = partner.commercial_partner_id

            account = getattr(partner, data["field_name"])
            if not account or account == ref_account:
                new_account = self.env["account.account"].create(
                    {
                        "code": data["code_template"] % partner.id,
                        "name": partner.name,
                        "tag_ids": [Command.set(ref_account.tag_ids.ids)],
                        "account_type": data["account_type"],
                        "tax_ids": [Command.set(ref_account.tax_ids.ids)],
                        "reconcile": True,
                    }
                )
                (partner | partner.child_ids).update({data["field_name"]: new_account})

    def _create_payable_account(self):
        "See _create_property_account doc string"
        self._create_property_account("payable")

    def _create_receivable_account(self):
        "See _create_property_account doc string"
        # Protect against double creation
        partner = self.commercial_partner_id
        code = _PROPERTY_ACCOUNT_DATA["receivable"]["code_template"] % partner.id
        existing = self.env["account.account"].search([("code", "=", code)])
        if existing:
            (partner | partner.child_ids).update(
                {"property_account_receivable_id": existing.id},
            )
        self._create_property_account("receivable")

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)

        for partner in result.filtered("supplier_rank"):
            partner._create_payable_account()

        return result

    def write(self, vals):
        """Handle property accounts creation or update

        When a partner becomes a supplier its payable account is automatically created.

        When a partner with a specific receivable account becomes the child of another
        with the default receivable account, it is copied to the parent and renamed
        according to the parent's name.
        """

        old_recv_acc = False
        if "parent_id" in vals:
            old_recv_acc = self.property_account_receivable_id

        result = super().write(vals)

        if "supplier_rank" in vals and vals["supplier_rank"]:
            self._create_payable_account()

        if old_recv_acc:
            data = _PROPERTY_ACCOUNT_DATA["receivable"]
            ref_account = self.env["ir.property"]._get(
                data["field_name"], "res.partner"
            )
            if (
                old_recv_acc != ref_account
                and self.parent_id.property_account_receivable_id == ref_account
            ):
                self.parent_id.property_account_receivable_id = old_recv_acc.id
                old_recv_acc.update(
                    {
                        "code": data["code_template"] % self.parent_id.id,
                        "name": self.parent_id.name,
                    }
                )

        return result
