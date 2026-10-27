import base64
from collections import defaultdict

from odoo import _, fields, models


def _by_id(env, data, attr, model):
    ids = tuple({item[attr][0] for item in data})
    return {obj.id: obj for obj in env[model].search([("id", "in", ids)])}


def _concatenate_address(partner):
    chunks = [partner.street, partner.street2, partner.zip, partner.country_id.name]
    return " ".join(c for c in chunks if c)


class ShareholderRegister(models.TransientModel):
    _name = "commown_shareholder_register.register"
    _description = "Utility class to compute a shareholder register"

    date = fields.Date(
        string="Register at date (included)",
        help="Shareholder moves at this date will be included.",
    )
    report = fields.Binary("Shareholder Register", readonly=True)
    report_name = fields.Char(string="Filename", size=256, readonly=True)

    def get_shareholders(self):
        """Return a dictionnary with following structure to describe the shareholders::
        {
            "warnings": [],
            "partners": {
                <partner_obj>: {
                    "total": <total amount of its shares in €>,
                    "college": <highest college of the partner>,
                    "address": <partner's postal address>,
                    "phone": <partner's phone>,
                    "total_ratio": <total amount / grand total amount>,
                }
            },
            "colleges": {
                <college_obj>: {
                    "partners": [<partner_obj>],
                    "total": <total amount of its partner shares in €>,
                    "share_number": <number of shares>,
                    "shareholder_number": <number of shareholders>,
               }
            },
            "total": {
                "balance": <total amount of all shares in €>,
                "share_number": <number of shares>,
                "shareholder_number": <number of shareholders>,
            },
        }
        """
        nominal_share_amount = self.env.company.nominal_share_amount
        cats = self.env["commown_shareholder_register.category"].search([])
        by_account = {c.account_id: c for c in cats}
        data = self.env["account.move.line"].read_group(
            [
                ("account_id", "in", cats.mapped("account_id.id")),
                ("partner_id", "!=", False),
                ("date", "<=", self.date),
                ("partner_id.active", "=", True),
            ],
            ["account_id", "partner_id", "balance:sum"],
            ["account_id", "partner_id"],
            lazy=False,
        )

        accounts = _by_id(self.env, data, "account_id", "account.account")

        # Aggregate shares by **commercial** partners:
        # - compute commercial partners at once for performance
        _partners = self.env["res.partner"].browse(i["partner_id"][0] for i in data)
        _commercial_partners = _partners.mapped("commercial_partner_id")
        partners = {p.id: p.commercial_partner_id for p in _partners}
        # - sum balances by (account, commercial partner)
        balances = defaultdict(float)
        for item in data:
            account = accounts[item["account_id"][0]]
            partner = partners[item["partner_id"][0]]
            balances[(account, partner)] += item["balance"]

        result = {
            "warnings": [],
            "partners": {},
            "colleges": {},
            "total": {
                "balance": 0,
            },
        }

        for (account, partner), balance in balances.items():
            cat = by_account[account]

            if -balance >= cat.min_share_number * nominal_share_amount:
                partner_data = result["partners"].setdefault(
                    partner,
                    {
                        "total": 0,
                        "college": self.env["commown_shareholder_register.college"],
                        "address": _concatenate_address(partner),
                        "phone": partner.mobile or partner.phone or "",
                    },
                )
                partner_data["total"] -= balance
                if partner_data["college"].rank < cat.college_id.rank:
                    partner_data["college"] = cat.college_id

                result["total"]["balance"] -= balance

            elif balance > 0:
                result["warnings"].append(
                    _("The partner %s has a negative share number") % partner.name
                )
            elif balance < 0:
                result["warnings"].append(
                    _(
                        "The partner %(part_name)s has not enough shares for college"
                        " %(college_name)s"
                    )
                    % {"part_name": partner.name, "college_name": cat.college_id.name}
                )

        for partner, partner_data in result["partners"].items():
            partner_data["share_number"] = partner_data["total"] / nominal_share_amount
            partner_data["total_ratio"] = (
                partner_data["total"] / result["total"]["balance"]
            )

            college = partner_data["college"]
            result["colleges"].setdefault(college, {"total": 0, "partners": []})[
                "total"
            ] += partner_data["total"]
            result["colleges"][college]["partners"].append(partner)

        for college in result["colleges"].keys():
            result["colleges"][college]["share_number"] = (
                result["colleges"][college]["total"] / nominal_share_amount
            )
            result["colleges"][college]["shareholder_number"] = len(
                result["colleges"][college]["partners"]
            )

        result["total"]["share_number"] = (
            result["total"]["balance"] / nominal_share_amount
        )
        result["total"]["shareholder_number"] = len(result["partners"])

        return result

    def generate_register(self):
        report = (
            self.env["ir.actions.report"]
            ._get_report_from_name("commown_shareholder_register.spreadsheet")
            .ensure_one()
        )
        result = report._render(report, self.ids)[0]
        self.write(
            {
                "report": base64.encodebytes(result),
                "report_name": "register.ods",
            }
        )

        return {
            "type": "ir.actions.act_multi",
            "actions": [
                {
                    "name": "register",
                    "type": "ir.actions.act_url",
                    "url": "web/content/?model=%s&id=%d&filename_field=report_name&"
                    "field=report&download=true&filename=%s"
                    % (self._name, self.id, self.report_name),
                    "target": "current",
                },
                {"type": "ir.actions.act_window_close"},
            ],
        }
