from base64 import b64decode

import magic

from odoo import _, api, fields, models, tools


class FileTooBig(Exception):  # noqa: B903
    def __init__(self, field, msg):
        self.field = field
        self.msg = msg


class CommownPartner(models.Model):
    _inherit = "res.partner"

    auto_widget_binary_fields = [
        "id_card1",
        "id_card2",
        "proof_of_address",
        "company_record",
    ]

    max_doc_image_size = (1240, 1754)
    max_doc_size_Mo = 5

    _binary_field_policy = (
        "Images are resized to %dx%d and, all files are limited to %dMo."
        % (max_doc_image_size + (max_doc_size_Mo,))
    )

    id_card1 = fields.Binary(
        "ID card",
        attachment=True,
        store=True,
        help=("This field holds a file to store the ID card. " + _binary_field_policy),
    )

    id_card2 = fields.Binary(
        "ID card (2)",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store the ID card (2). " + _binary_field_policy
        ),
    )

    proof_of_address = fields.Binary(
        "Proof of address",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store a proof of address. "
            + _binary_field_policy
        ),
    )

    company_record = fields.Binary(
        "Company record",
        attachment=True,
        store=True,
        help=(
            "This field holds a file to store a company record. " + _binary_field_policy
        ),
    )

    def _apply_bin_field_size_policy(self, vals):
        """Apply the binary field limit policy: resize images, raise if the
        final value is still too big.
        """
        for field in self.auto_widget_binary_fields:
            posted_value = vals.get(field)
            if posted_value:
                if isinstance(posted_value, str):
                    b64value = posted_value.encode("ascii")
                elif isinstance(posted_value, bytes):
                    b64value = posted_value
                else:
                    raise ValueError(
                        "The type %s is not covered by this function"
                        % type(posted_value)
                    )
                value = b64decode(b64value)
                if magic.from_buffer(value, mime=True).startswith("image"):
                    vals[field] = tools.image_resize_image(
                        b64value, avoid_if_small=True, size=self.max_doc_image_size
                    )
                    value = b64decode(vals[field])
                if len(value) > 1024 * 1024 * self.max_doc_size_Mo:
                    raise FileTooBig(
                        field, _("File too big (limit is %dMo)") % self.max_doc_size_Mo
                    )

    @api.model
    def create(self, vals):
        self._apply_bin_field_size_policy(vals)
        return super().create(vals)

    def write(self, vals):
        self._apply_bin_field_size_policy(vals)
        return super().write(vals)
