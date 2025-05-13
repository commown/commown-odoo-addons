import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon={
        'external_dependencies_override': {
            'python': {
                'hal_codec': 'hal_codec @ git+https://github.com/fcayre/python-hal-codec.git@unique-link-keys',
            },
        },
    },
)
