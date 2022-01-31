# Copyright 2020 Commown SCIC SAS (https://commown.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Commown ergonomy: assets',
    'category': 'Accounting & Finance',
    'summary': 'Assets ergonomy improvements for Commown',
    'version': '12.0.1.0.0',
    'description': "Assets ergonomy improvements for Commown",
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'depends': [
        'account_asset_management',
    ],
    'data': [
        'views/account_asset.xml',
    ],
    'installable': True,
}
