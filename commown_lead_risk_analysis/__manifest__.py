{
    "name": "Commown lead risk analysis",
    "category": "Business",
    "summary": "Add risk analysis-related fields to leads",
    "version": "12.0.1.0.6",
    "description": "Risk analysis data storage for Commown leads",
    "author": "Commown SCIC SAS",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "crm",
        "partner_firstname",
        "product_rental",
    ],
    "data": [
        "views/crm_lead.xml",
        "views/crm_team.xml",
        "views/product_template.xml",
    ],
    "installable": True,
}
