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
        contract_model = self.env["contract.contract"]
        today = datetime.date.today()
        base_domain = [
            ("partner_id", "=", self.id),
            ("date_start", "<=", today),
            "|",
            ("date_end", "=", False),
            ("date_end", ">", today),
        ]

        f_path = osp.join(
            HERE, "..", *page.arch_fs.split(osp.sep)[1:-1], "meta_data.py"
        )
        with open(f_path) as fobj:
            meta_data = safe_eval(
                fobj.read(),
                {
                    "env": self.env,
                    "datetime": datetime,
                    "base_domain": base_domain,
                },
            )

        return contract_model.search(meta_data["contract_domain"])

    def self_troubleshooting_contracts(self, page_ref):
        page = self.env.ref("commown_self_troubleshooting." + page_ref)
        return self._self_troubleshooting_webpage_data(page)

    def self_troubleshooting_all_data(self):
        categories = defaultdict(list)
        page_refs = self.env["ir.model.data"].search(
            [
                ("module", "=", "commown_self_troubleshooting"),
                ("model", "=", "website.page"),
            ]
        )

        for ref in page_refs:
            page = self.env.ref(ref.module + "." + ref.name)
            contracts = self._self_troubleshooting_webpage_data(page)
            if contracts:
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
