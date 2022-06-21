# Copyright (C) 2021 - Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown Cooperative campaign',
    'category': 'Business',
    'description': ('Use telecommown web services to handle discounts'
                    ' from multi-partners cooperative campaigns'),
    'version': '10.0.1.2.1',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'external_dependencies': {
        'python': ['requests', 'phonenumbers', 'iso8601']
    },
    'depends': [
        'commown_contract_variable_discount',
        'queue_job',
        'keychain',
        'l10n_fr',
    ],
    'data': [
        'data/action_coupon.xml',
        'data/ir_config_parameter.xml',
        'data/keychain_accounts.xml',
        'views/coupon.xml',
        'views/wizard_late_optin.xml',
    ],
    'installable': True,
}
