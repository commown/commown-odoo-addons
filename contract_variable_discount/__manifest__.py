# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Contract variable discount',
    'category': 'Contract Management',
    'version': '12.0.1.2.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'depends': [
        'contract',
        'web_domain_field',
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
