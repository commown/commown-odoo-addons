{
    "name": "Website sale coupon",
    "category": "Business",
    "summary": (
        "Manage promotion campaigns with or without coupons."
        " Coupons are secret codes that customers can get (paid or for free)"
        " to get an advantage when they buy a product on the online shop."
    ),
    "version": "12.0.1.1.0",
    "description": (
        "This module is intended to manage promotion campaigns.\n"
        "These promotion campaigns have optional start and end validity dates."
        " According to the campaign setup, customers must either enter a unique"
        " secret code or directly the campaign name to benefit from the"
        " advantages granted by the campaign when they buy a product on the"
        " online shop.\n"
        "Important note: the present module does NOT implement any advantage,"
        " which must be implemented in dedicated modules. This is on purpose,"
        " as these advantages can be various, not necessarily an immediate"
        " price reduction."
    ),
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "website_sale",
    ],
    "external_dependencies": {},
    "data": [
        "security/ir.model.access.csv",
        "views/backoffice.xml",
        "views/website.xml",
        "views/wizard_create_multiple_coupons.xml",
    ],
    "installable": True,
}
