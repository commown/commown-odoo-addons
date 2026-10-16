from odoo import _, fields, models


class AccountAssetMassRemove(models.TransientModel):
    _name = "account.asset.mass.remove"
    _description = "Mass Asset Removal Wizard"

    date_remove = fields.Date(required=True)

    def mass_remove(self):
        assets = self.env["account.asset"].browse(self.env.context.get("active_ids"))

        def lref(ref):
            return self.env.ref("commown_assets_ergonomy.%s" % ref)

        journal = lref("various_operations_journal")
        account = lref("various_expenses_account")

        created_entries = self.env["account.move"]

        for asset in assets:
            asset.remove()
            wiz = (
                self.env["account.asset.remove"]
                .with_context(active_id=asset.id)
                .create(
                    {
                        "force_date": self.date_remove,
                        "posting_regime": "residual_value",
                        "account_residual_value_id": account.id,
                    }
                )
            )
            window_act = wiz.remove()

            entry = self.env["account.move"].search(window_act["domain"])
            entry.journal_id = journal.id
            entry.ref = (
                entry.ref + " - Sortie d'actifs (absence d'avantages économiques)"
            )

            created_entries |= entry

        return {
            "name": _("Created Journal Entries for Removed Assets"),
            "view_mode": "tree,form",
            "res_model": "account.move",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": [("id", "in", created_entries.ids)],
        }
