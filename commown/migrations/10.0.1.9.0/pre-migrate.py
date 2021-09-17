from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):

    fields_moves = {
        ('commown', 'commown_shipping', 'crm.lead'): [
            'delivery_date',
            'expedition_date',
            'expedition_ref',
            'expedition_status',
            'expedition_status_fetch_date',
            'expedition_urgency_mail_sent',
            'on_delivery_email_template_id',
            'send_email_on_delivery',
            'start_contract_on_delivery',
        ],

        ('commown', 'commown_lead_risk_analysis', 'crm.lead'): [
            'address_hesitation',
            'billing_address_validated',
            'comments',
            'delivery_address_validated',
            'email_boost',
            'email_rating',
            'email_ultimatum',
            'email_validated',
            'first_phone_call',
            'global_feeling',
            'identity_validated',
            'initial_data_notes',
            'mobile_validated',
            'orders_description',
            'questions',
            'registered_mail_sent',
            'second_phone_call',
            'sent_collective_email',
            'technical_skills',
            'third_phone_call',
            'webid_notes',
            'webid_rating',
            'webid_unknown',
            'web_searchurl',
        ],
    }

    for (from_mod, to_mod, model), fields in fields_moves.items():
        openupgrade.update_module_moved_fields(
            env.cr, model, fields, from_mod, to_mod)

    rm_fields = '''
custom_lead_view_id
website_sale_affiliate_product_restriction sale.affiliate restriction_product_tmpl_ids
website_sale_affiliate_portal sale.affiliate gain_type
website_sale_affiliate_portal sale.affiliate gain_value
website_sale_affiliate_portal sale.affiliate partner_description
rating_project_issue_nps project.project net_promoter_score
rating_project_issue_nps rating.rating net_promoter_score
product_rental product.product rental_price
product_rental product.template rental_price
'''
