import datetime
import os.path as osp
from collections import defaultdict

from odoo import models
from odoo.tools.safe_eval import safe_eval

# from odoo.http import request

HERE = osp.dirname(__file__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _self_troubleshooting_webpage_data(self, page):
        today = datetime.date.today()
        base_domain = [
            ("partner_id.commercial_partner_id", "=", self.commercial_partner_id.id),
            ("date_start", "<=", today),
            "|",
            ("date_end", "=", False),
            ("date_end", ">", today),
        ]

        f_path = osp.join(
            HERE, "..", *page.arch_fs.split(osp.sep)[1:-1], "meta_data.py"
        )
        with open(f_path) as fobj:
            return safe_eval(
                fobj.read(),
                {
                    "env": self.env,
                    "datetime": datetime,
                    "base_domain": base_domain,
                },
            )

    def self_troubleshooting_contracts(self, page_ref):
        page = self.env.ref("commown_self_troubleshooting." + page_ref)
        meta_data = self._self_troubleshooting_webpage_data(page)
        if meta_data.get("contract_domain", None) is None:
            return self.env["contract.contract"]
        else:
            return self.env["contract.contract"].search(meta_data["contract_domain"])

    def self_troubleshooting_all_data(self):
        page_refs = self.env["ir.model.data"].search(
            [
                ("module", "=", "commown_self_troubleshooting"),
                ("model", "=", "website.page"),
            ]
        )

        pages = []
        for ref in page_refs:
            page = self.env.ref(ref.module + "." + ref.name)
            meta_data = self._self_troubleshooting_webpage_data(page)
            if meta_data.get("contract_domain", None) is None or self.env[
                "contract.contract"
            ].search(meta_data["contract_domain"]):
                pages.append((meta_data.get("sequence", 0), page))

        categories = defaultdict(list)
        for sequence, page in sorted(pages):
            categories[page.website_meta_title].append(page)

        return [
            {
                "title": title,
                "pages": [
                    {
                        "url_path": page.url,
                        "description": page.website_meta_description,
                    }
                    for page in pages
                ],
            }
            for title, pages in categories.items()
        ]
