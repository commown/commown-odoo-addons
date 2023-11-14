from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def self_troubleshooting_contracts(self, page_ref):
        page = self.env.ref("commown_self_troubleshooting." + page_ref)
        item = self.env["commown_self_troubleshooting.item"].search(
            [("website_page_id", "=", page.id)],
        )
        return item.get_contracts(self)

    def self_troubleshooting_all_data(self):
        all_items = self.env["commown_self_troubleshooting.item"].search([])

        result = []
        last_cat = None  # items are ordered by categories

        for item in all_items:
            if item.requires_contract and not item.get_contracts(self):
                continue
            link = item.get_link()
            if link["category"] != last_cat:
                last_cat = link["category"]
                cat = {"title": last_cat, "pages": []}
                result.append(cat)

            else:
                cat = result[-1]

            cat["pages"].append({"url_path": link["url"], "description": link["text"]})

        return result
