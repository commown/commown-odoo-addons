from odoo import _, fields, models

NOMINAL_SHARE_AMOUNT = 20

SHARE_ACCOUNT_IDENTIFIER = "1013%"

SHARE_TYPE_DATA = {
    "10134000": {  # Porteurs de Projet
        "nom_part": "Parts sociales Porteurs de Projet",
        "college_rank": 80,
        "letter": "A",
        "min_share_number": 100,
    },
    "10139000": {  # Salariés
        "nom_part": "Parts sociales Salariés",
        "college_rank": 70,
        "letter": "A",
        "min_share_number": 5,
    },
    "10137000": {  # Producteurs
        "nom_part": "Parts sociales Producteurs",
        "college_rank": 60,
        "letter": "C",
        "min_share_number": 25,
    },
    "10136000": {  # Soutiens Financiers
        "nom_part": "Parts sociales Soutiens Financier",
        "college_rank": 40,
        "letter": "D",
        "min_share_number": 5,
    },
    "10138000": {  # Communicants
        "nom_part": "Parts sociales Communicants",
        "college_rank": 30,
        "letter": "B",
        "min_share_number": 1,
    },
    "10135000": {  # Bénéficiaires
        "nom_part": "Parts sociales Bénéficiaires",
        "college_rank": 20,
        "letter": "B",
        "min_share_number": 1,
    },
}


for item in SHARE_TYPE_DATA.values():
    item["min_share_amount"] = item["min_share_number"] * NOMINAL_SHARE_AMOUNT


def _by_id(env, data, attr, model):
    ids = tuple({item[attr][0] for item in data})
    return {obj.id: obj for obj in env[model].search([("id", "in", ids)])}


def _concatenate_address(partner):
    chunks = [partner.street, partner.street2, partner.zip, partner.country_id.name]
    return " ".join(c for c in chunks if c)


class ShareholderRegister(models.TransientModel):
    _name = "commown_shareholder_register.register"
    _description = "Utility class to compute a shareholder register"

    date = fields.Datetime(
        string="Date",
        help="Date of the register",
    )

    def get_shareholders(self):
        data = self.env["account.move.line"].read_group(
            [
                ("account_id.code", "=like", SHARE_ACCOUNT_IDENTIFIER),
                ("partner_id", "!=", False),
                ("date", "<", self.date),
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

            if -item["balance"] >= SHARE_TYPE_DATA[account.code]["min_share_amount"]:
                partner_data = result["partners"].setdefault(
                    partner,
                    {
                        "total": 0,
                        "college": {"college_rank": 0},
                        "address": _concatenate_address(partner),
                        "phone": partner.phone or "",
                    },
                )
                partner_data["total"] -= item["balance"]
                if (
                    partner_data["college"]["college_rank"]
                    < SHARE_TYPE_DATA[account.code]["college_rank"]
                ):
                    partner_data["college"] = SHARE_TYPE_DATA[account.code]

                result["total"]["balance"] -= item["balance"]

            elif item["balance"] > 0:
                result["warnings"].append(
                    _("The partner %s has a negative share number") % partner.name
                )
            elif item["balance"] < 0:
                result["warnings"].append(
                    _("The partner %s has not enough shares for college %s")
                    % (partner.name, SHARE_TYPE_DATA[account.code]["letter"])
                )

        for partner, partner_data in result["partners"].items():
            partner_data["share_number"] = partner_data["total"] / NOMINAL_SHARE_AMOUNT
            partner_data["total_ratio"] = (
                partner_data["total"] / result["total"]["balance"]
            )

            college = partner_data["college"]["letter"]
            result["colleges"].setdefault(college, {"total": 0, "partners": [],},)[
                "total"
            ] += partner_data["total"]
            result["colleges"][college]["partners"].append(partner)

        for college in result["colleges"].keys():
            result["colleges"][college]["share_number"] = (
                result["colleges"][college]["total"] / NOMINAL_SHARE_AMOUNT
            )
            result["colleges"][college]["shareholder_number"] = len(
                result["colleges"][college]["partners"]
            )

        result["total"]["share_number"] = (
            result["total"]["balance"] / NOMINAL_SHARE_AMOUNT
        )
        result["total"]["shareholder_number"] = len(result["partners"])

        return result
