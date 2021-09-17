from odoo import fields, models


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    transaction_label = fields.Text(
        string='Payment label', default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #START#, #END#, #INV# (invoice number)'),
    )
