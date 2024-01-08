from odoo import _, api, models

from .colissimo_utils import MAX_ADDRESS_SIZE_COLISSIMO, delivery_data

ADDRESS_LENGTH_ERROR = (
    "The street field size cannot exceed %d" % MAX_ADDRESS_SIZE_COLISSIMO
)


class ResPartner(models.Model):
    _inherit = "res.partner"
    MAX_ADDRESS_SIZE = MAX_ADDRESS_SIZE_COLISSIMO

    _sql_constraints = [
        (
            "street_max_size_colissimo",
            "CHECK(CHAR_LENGTH(street) <= %d)" % MAX_ADDRESS_SIZE_COLISSIMO,
            ADDRESS_LENGTH_ERROR,
        ),
        (
            "street2_max_size_colissimo",
            "CHECK(CHAR_LENGTH(street2) <= %d)" % MAX_ADDRESS_SIZE_COLISSIMO,
            ADDRESS_LENGTH_ERROR,
        ),
    ]

    @api.multi
    def colissimo_delivery_data(self, raise_on_error=True):
        self.ensure_one()
        return delivery_data(self, raise_on_error=raise_on_error)

    @classmethod
    def validate_street_lines(cls, data, error, error_message):
        street_error = False
        for field in ("street", "street2"):
            value = data.get(field)
            if value and len(value) > MAX_ADDRESS_SIZE_COLISSIMO:
                error[field] = "error"
                street_error = True

        if street_error:
            error_message.append(
                _("Address lines' length is limited to %s. Please fix.")
                % MAX_ADDRESS_SIZE_COLISSIMO
            )
