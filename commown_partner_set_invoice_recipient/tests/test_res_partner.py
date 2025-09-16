from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class ResPartnerInvoiceActionTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Setup test data:
        a company with a contract, and two partners linked to that company
        """
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
        cls.company = cls.env["res.partner"].create(
            {"name": "Company", "is_company": True}
        )

        # If that module is installed, then the auto_merge might crash if
        # the environnement company has no payment mode.
        # As such, we add this situationnal import which creates relevant data.
        if cls.env["ir.module.module"].search(
            [
                ("name", "=", "account_invoice_merge_auto_pay"),
                ("state", "=", "installed"),
            ]
        ):  # pragma: no cover
            from odoo.addons.account_invoice_merge_auto_pay.tests.common import (
                inject_payment_data,
            )

            inject_payment_data(cls, cls.company)

        cls.company_worker = cls.env["res.partner"].create(
            {
                "name": "Test worker",
                "is_company": False,
                "parent_id": cls.company.id,
            }
        )

        product = cls.env.ref("product.product_product_1")
        cls.contract = cls.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": cls.company.id,
                "invoice_partner_id": cls.company.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Services from #START# to #END#",
                            "quantity": 1,
                            "uom_id": product.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2018-02-15",
                            "recurring_next_date": "2018-02-15",
                        },
                    )
                ],
            }
        )

    def test_action(self):
        "Action must reattribute contracts and draft invoices"
        inv_partner = self.company_worker.copy({"type": "invoice"})
        draft_inv = self.contract._recurring_create_invoice()

        inv_partner.action_set_as_invoice_recipient()

        self.assertEqual(self.contract.invoice_partner_id, inv_partner)
        self.assertEqual(draft_inv.partner_id, inv_partner)
