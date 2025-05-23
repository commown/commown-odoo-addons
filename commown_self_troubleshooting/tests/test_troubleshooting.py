from odoo.tests import TransactionCase


class SelfTroubleshootingItemTC(TransactionCase):
    def test_name_get(self):
        item_cat = self.env.ref("commown_self_troubleshooting.generic-issue-ts-item")
        item_link = self.env["commown_self_troubleshooting.item"].create(
            {
                "link_url": "https://commown.coop",
                "link_text": "Commown Website",
                "category_id": item_cat.category_id.id,
            },
        )

        self.assertEqual(item_cat.display_name, "Self-troubleshoot Generic Issue")
        self.assertEqual(item_link.display_name, "Commown Website")
