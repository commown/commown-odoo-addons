from odoo import _, fields, models


class AccountAssetMassRemove(models.TransientModel):
    _name = "account.asset.mass.remove"
    _description = "Mass Asset Removal Wizard"

    date_remove = fields.Date(required=True)
    notes = fields.Text(readonly=True)

    def mass_remove(self):
        assets = self.env["account.asset"].browse(self.env.context.get("active_ids"))

        def lref(ref):
            return self.env.ref("commown_assets_ergonomy.%s" % ref)

        journal = lref("various_operations_journal")
        account = lref("various_expenses_account")

        created_entries = self.env["account.move"]

        error_log = ""
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
            try:
                with self.env.cr.savepoint():
                    window_act = wiz.remove()
            except Exception as exc:
                asset_ref = asset.name
                if asset.code:  # pragma: no cover
                    asset_ref = "[%s] %s" % (asset.code, asset_ref)

                error_log += _(
                    "\nError while removing asset '{ref}': {exception}"
                ).format(ref=asset_ref, exception=repr(exc))
                continue

            entry = self.env["account.move"].search(window_act["domain"])
            entry.journal_id = journal.id
            entry.ref = (
                entry.ref + " - Sortie d'actifs (absence d'avantages économiques)"
            )

            created_entries |= entry

        if error_log:
            result_view = lref("view_account_asset_mass_remove_wizard_results")
            self.notes = _("Mass Asset Removal results") + ":\n" + error_log
            return {
                "name": _("Mass Asset Removal result"),
                "res_id": self.id,
                "view_mode": "form",
                "res_model": "account.asset.mass.remove",
                "view_id": result_view.id,
                "target": "new",
                "type": "ir.actions.act_window",
                "context": {"created_entries_ids": created_entries.ids},
            }

        return {
            "name": _("Created Journal Entries for Removed Assets"),
            "view_mode": "tree,form",
            "res_model": "account.move",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": [("id", "in", created_entries.ids)],
        }

    def view_asset_moves(self):
        domain = [("id", "in", self.env.context.get("created_entries_ids", []))]

        return {
            "name": _("Created Journal Entries for Removed Assets"),
            "view_mode": "tree,form",
            "res_model": "account.move",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": domain,
        }
