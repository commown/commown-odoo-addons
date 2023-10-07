import base64

from odoo import _, api, fields, models


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
        nominal_share_amount = self.env.user.company_id.nominal_share_amount
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

        partners = _by_id(self.env, data, "partner_id", "res.partner")
        accounts = _by_id(self.env, data, "account_id", "account.account")

        result = {
            "warnings": [],
            "partners": {},
            "colleges": {},
            "total": {
                "balance": 0,
            },
        }

        for item in data:
            account = accounts[item["account_id"][0]]
            partner = partners[item["partner_id"][0]]

            cat = by_account[account]

            if -item["balance"] >= cat.min_share_number * nominal_share_amount:
                partner_data = result["partners"].setdefault(
                    partner,
                    {
                        "total": 0,
                        "college": self.env["commown_shareholder_register.college"],
                        "address": _concatenate_address(partner),
                        "phone": partner.phone or "",
                    },
                )
                partner_data["total"] -= item["balance"]
                if partner_data["college"].rank < cat.college_id.rank:
                    partner_data["college"] = cat.college_id

                result["total"]["balance"] -= item["balance"]

            elif item["balance"] > 0:
                result["warnings"].append(
                    _("The partner %s has a negative share number") % partner.name
                )
            elif item["balance"] < 0:
                result["warnings"].append(
                    _("The partner %s has not enough shares for college %s")
                    % (partner.name, cat.college_id.name)
                )

        for partner, partner_data in result["partners"].items():
            partner_data["share_number"] = partner_data["total"] / nominal_share_amount
            partner_data["total_ratio"] = (
                partner_data["total"] / result["total"]["balance"]
            )

            college = partner_data["college"]
            result["colleges"].setdefault(college, {"total": 0, "partners": [],},)[
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

    @api.multi
    def generate_register(self):
        report = (
            self.env["ir.actions.report"]
            ._get_report_from_name("commown_shareholder_register.spreadsheet")
            .ensure_one()
        )
        result = report.render(self.ids)[0]
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
