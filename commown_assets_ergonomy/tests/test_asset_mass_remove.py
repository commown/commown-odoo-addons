from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class AssetMassRemoveTC(TransactionCase):
    @classmethod
    def lref(cls, ref):
        return cls.env.ref("commown_assets_ergonomy.%s" % ref)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.companies.filtered("chart_template_id")[0]
        if cls.env.company != company:  # pragma: no cover
            cls.env.company = company
            cls.lref("various_operations_journal").company_id = company
            cls.lref("various_expenses_account").company_id = company

        journal_purchase = cls.env["account.journal"].search(
            [("company_id", "=", cls.env.company.id), ("type", "=", "purchase")],
            limit=1,
        )
        account_assets = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.env.company.id),
                ("account_type", "=", "asset_current"),
            ],
            limit=1,
        )
        company_loss_account = (
            cls.env.company.account_journal_early_pay_discount_loss_account_id
        )
        account_expenses = cls.env["account.account"].search(
            [
                ("id", "!=", company_loss_account.id),
                ("company_id", "=", cls.env.company.id),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )

        profile = cls.env["account.asset.profile"].create(
            {
                "name": "Phones - 12 Month",
                "method_time": "number",
                "method_period": "month",
                "method_number": 12,
                "account_expense_depreciation_id": account_expenses.id,
                "account_asset_id": account_assets.id,
                "account_depreciation_id": account_assets.id,
                "journal_id": journal_purchase.id,
            }
        )

        cls.assets = cls.env["account.asset"].create(
            [
                {
                    "profile_id": profile.id,
                    "name": "Dummy asset %s" % i,
                    "purchase_value": 500,
                    "salvage_value": 0,
                    "date_start": "2026-10-01",
                }
                for i in range(1, 3)
            ]
        )
        cls.assets.validate()

    def _asset_remove_wizard(self, date):
        return (
            self.env["account.asset.mass.remove"]
            .with_context(active_ids=self.assets.ids)
            .create({"date_remove": date})
        )

    def test_mass_asset_remove_ok(self):
        wiz = self._asset_remove_wizard("2026-10-15")

        action = wiz.mass_remove()

        self.assertEqual({"removed"}, set(self.assets.mapped("state")))

        created_entries = self.env["account.move"].search(action["domain"])

        self.assertEqual(len(created_entries), 2)
        self.assertEqual(created_entries.line_ids.asset_id, self.assets)
        self.assertEqual(set(created_entries.mapped("state")), {"posted"})
        self.assertIn("Sortie d'actifs", created_entries[0].ref)

    def test_mass_asset_remove_error(self):
        "Any assets which cannot be removed shouldn't stop the removal of other assets"
        asset_1, asset_2 = self.assets
        dline = self.env["account.asset.line"].search(
            [
                ("asset_id", "=", asset_2.id),
                ("type", "=", "depreciate"),
                ("move_check", "=", False),
            ],
            order="line_date asc",
            limit=1,
        )
        dline.create_move()

        wiz = self._asset_remove_wizard("2026-10-15")
        res_action = wiz.mass_remove()
        action = wiz.with_context(**res_action["context"]).view_asset_moves()

        self.assertEqual(asset_1.state, "removed")
        self.assertEqual(asset_2.state, "open")
        self.assertIn(
            f"Error while removing asset '{asset_2.name}'",
            wiz.notes,
        )

        created_entries = self.env["account.move"].search(action["domain"])

        self.assertEqual(len(created_entries), 1)
        self.assertEqual(created_entries.line_ids.asset_id, asset_1)
        self.assertEqual(created_entries.state, "posted")
        self.assertIn("Sortie d'actifs", created_entries.ref)
