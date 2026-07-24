from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class ForceMoveLinePartnerTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

        cls.partner_1 = cls.env.ref("base.partner_demo_portal")
        cls.partner_2 = cls.partner_1.copy({"email": "test@test.coop"})

        cls.account = cls.env["account.account"].create(
            {
                "name": "Dummy account",
                "code": "12345",
                "account_type": "asset_current",
            }
        )

        cls.move = cls.env["account.move"].create(
            {
                "name": "Dummy move",
                "move_type": "entry",
                "partner_id": cls.partner_1.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test line 1",
                            "quantity": 1,
                            "price_unit": 50,
                            "product_id": cls().ref("product.product_product_1"),
                            "account_id": cls.account.id,
                        }
                    ),
                ],
            }
        )
        cls.payment = cls.env["account.payment"].create(
            {"partner_id": cls.partner_1.id, "move_id": cls.move.id}
        )

    def _force_partner_wizard(self, move, target_partner, user=None):
        ForcePartnerWiz = self.env["wizard.force.partner.on.move.line"].with_user(
            user or self.env.user
        )

        return ForcePartnerWiz.with_context(default_move_id=move.id).create(
            {
                "line_to_change_id": move.line_ids[0].id,
                "new_partner_id": target_partner.id,
            }
        )

    def test_wizard_ok(self):
        "Using the wizard should allow assignment of different partners across different move lines"
        # Default case: changing the partner directly on a move line related to a payment raises an error
        # (see _synchronize_from_moves from odoo/addons/account/models/account_payment.py:L798)
        with self.assertRaises(UserError) as exc:
            self.move.line_ids[0].partner_id = self.partner_2
        self.assertIn("share the same partner", exc.exception.args[0])

        # Using the wizard to force the partner change
        wizard = self._force_partner_wizard(self.move, self.partner_2)
        wizard.execute()

        self.move.line_ids.invalidate_recordset()
        self.assertEqual(
            self.move.mapped("line_ids.partner_id"), (self.partner_1 | self.partner_2)
        )

        # Checking the last note's content to get the change notification
        notif_message = self.move.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref("mail.mt_note")
        )[0]

        self.assertIn("Partner changed", notif_message.body)
        self.assertIn(self.partner_1.display_name, notif_message.body)
        self.assertIn(self.partner_2.display_name, notif_message.body)

    def test_wizard_model_access(self):
        "Only members of the 'Invoicing / Manager' group should be able to use the software"
        demo_user = self.env.ref("base.user_demo")
        inv_manager_group = self.env.ref("account.group_account_manager")

        # Case 1: User is an invoicing manager
        demo_user.groups_id += inv_manager_group

        wiz_ok = self._force_partner_wizard(self.move, self.partner_2, user=demo_user)
        self.assertTrue(wiz_ok)

        # Case 2: User is not an invoicing manager
        demo_user.groups_id -= inv_manager_group

        with self.assertRaises(AccessError):
            _ = self._force_partner_wizard(self.move, self.partner_2, user=demo_user)
