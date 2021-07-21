# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Contract variable discount',
    'category': 'Contract Management',
    'version': '10.0.1.0.1',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'contract',
    ],
    'data': [
        'data/report.xml',
        'data/report_simulate_payments.xml',
        'security/ir.model.access.csv',
        'views/contract.xml',
        'views/contract_template.xml',
        'views/discount.xml',
    ],
    'installable': True,
}
