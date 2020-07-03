from odoo import fields, models

from .colissimo_utils import ship


class ParcelType(models.Model):
    _name = "commown.parcel.type"
    _description = "Parcel description"

    name = fields.Char("Parcel name", required=True, index=True)
    technical_name = fields.Char("Parcel technical name", required=True, index=True)
    weight = fields.Float("Weight (kg)", required=True)
    insurance_value = fields.Float("Insurance value (€)", required=True, default=0.0)
    is_return = fields.Boolean("Return parcel", required=True, default=False)

    def _compute_default_sender(self):
        return self.env.ref("base.main_company").partner_id

    sender = fields.Many2one(
        "res.partner", string="Sender", required=True, default=_compute_default_sender
    )

    _sql_constraints = [
        (
            "uniq_technical_name",
            "UNIQUE (technical_name)",
            "Parcel technical names must be unique.",
        ),
        ("check_weight", "check(weight > 0)", "The weight must be > 0!"),
        (
            "check_insurance_value",
            "check(insurance_value >= 0)",
            "Insurance value must be >= 0!",
        ),
    ]

    def colissimo_label(self, account, sender, recipient, ref=""):
        """ Return the meta data and the PDF data of a colissimo label from:

        - account: a keychain.account entity which namespace is "colissimo"
        - sender: the sender res.partner entity
        - recipient: the recipient res.partner entity
        - ref: a string reference to be printed on the parcel
        """
        self.ensure_one()

        commercial_name = self.env.ref("base.main_company").name

        return ship(
            account.login,
            account._get_password(),
            sender=sender,
            recipient=recipient,
            order_number=ref,
            commercial_name=commercial_name,
            weight=self.weight,
            insurance_value=self.insurance_value,
            is_return=self.is_return,
        )
