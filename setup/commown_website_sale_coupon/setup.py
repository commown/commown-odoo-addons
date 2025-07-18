import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon={
        'external_dependencies_override': {
            'python': {
                'pdfminer.six': 'pdfminer.six==20220319',
            },
        },
    },
)
