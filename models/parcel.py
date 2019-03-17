# coding: utf-8

from odoo import models, fields

from colissimo_utils import ship


class ParcelType(models.Model):
    _name = 'commown.parcel.type'
    _description = 'Parcel description'

    name = fields.Char('Parcel name', required=True, index=True)
    weight = fields.Float('Weight (kg)', required=True)
    insurance_value = fields.Float(
        'Insurance value (€)', required=True, default=0.)
    is_return = fields.Boolean('Return parcel', required=True, default=False)

    _sql_constraints = [
        ('uniq_name', 'UNIQUE (name)', 'Parcel names must be unique.'),
        ('check_weight', 'check(weight > 0)', 'The weight must be > 0!'),
        ('check_insurance_value', 'check(insurance_value >= 0)',
         'Insurance value must be >= 0!'),
    ]

    def colissimo_label(self, account, sender, recipient, reference=''):
        self.ensure_one()

        commercial_name = self.env.ref('base.main_company').name

        if self.is_return:
            sender, recipient = recipient, sender

        keychain_account = self.env['keychain.account'].sudo().retrieve([
            ('namespace', '=', 'colissimo'),
            ('login', '=', account),
        ]).ensure_one()

        return ship(keychain_account.login,
                    keychain_account._get_password(),
                    sender=sender,
                    recipient=recipient,
                    order_number=reference,
                    commercial_name=commercial_name,
                    weight=self.weight,
                    insurance_value=self.insurance_value,
                    is_return=self.is_return,
                    )
