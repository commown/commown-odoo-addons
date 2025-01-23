from odoo import fields, models


class SupportedProductTemplate(models.Model):
    """Add groups to products, where users who bought the product are
    automatically added.
    """

    _inherit = "product.template"

    sale_line_warn_msg = fields.Text(translate=True)

    is_user_lang_fr = fields.Boolean(
        compute="_compute_is_user_lang_fr",
        store=False,
    )

    def _compute_is_user_lang_fr(self):
        self.update({"is_user_lang_fr": self.env.user.lang == "fr_FR"})
