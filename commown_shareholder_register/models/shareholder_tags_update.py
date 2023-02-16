import io

from odoo import api, fields, models

SHAREHOLDER_TAG_XML_ID = "commown_shareholder_register.shareholder_tag"
COLLEGE_A_XML_ID = "commown_shareholder_register.shareholder_tag_col_A"
COLLEGE_B_XML_ID = "commown_shareholder_register.shareholder_tag_col_B"
COLLEGE_C_XML_ID = "commown_shareholder_register.shareholder_tag_col_C"
COLLEGE_D_XML_ID = "commown_shareholder_register.shareholder_tag_col_D"


class ShareholderTagsUpdate(models.TransientModel):
    _name = "commown_shareholder_register.shareholder_tags_update"
    _description = "Utility class to update partner shareholder's tag"

    date = fields.Datetime(
        string="Date",
        help="Date of the register",
    )

    @api.multi
    def action_update_partners_tag(self):
        register = self.env["commown_shareholder_register.register"].create(
            {"date": self.date},
        )
        shareholders_data = register.get_shareholders()
        shareholder_tag = self.env.ref(SHAREHOLDER_TAG_XML_ID)
        college_tag_ids = {
            "A": self.env.ref(COLLEGE_A_XML_ID).id,
            "B": self.env.ref(COLLEGE_B_XML_ID).id,
            "C": self.env.ref(COLLEGE_C_XML_ID).id,
            "D": self.env.ref(COLLEGE_D_XML_ID).id,
        }

        self.env.cr.execute(
            "delete from res_partner_res_partner_category_rel where category_id in %s",
            [tuple(college_tag_ids.values()) + (shareholder_tag.id,)],
        )

        sql = io.StringIO()
        sql.writelines(
            "%d\t%d\n%d\t%d\n"
            % (partner.id, college_tag_ids[college], partner.id, shareholder_tag.id)
            for college, data in shareholders_data["colleges"].items()
            for partner in data["partners"]
        )
        sql.seek(0)

        self.env.cr.copy_from(
            sql,
            "res_partner_res_partner_category_rel",
            columns=("partner_id", "category_id"),
        )

        self.env.cache.invalidate()
