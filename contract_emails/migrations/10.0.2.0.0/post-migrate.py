# Migrate planned mail already sent
# --
#
# The aim is not to resend planned emails, by inserting entries from
# the old contract_emails_planned_mail_template in the new table
# (contract_emails_planned_mail_sent).
#
# Some are not transfered to the new table, those which were manually
# created: no generator is defined on their contract template. This is
# not a problem since they are pretty old and will not be resent if a
# generator is created for them, unless the generator's max_delay_days
# is set to a ridiculuously high value (the default is 30 days), as
# can be audited with the following request:
#
# SELECT PMT.id AS pmt_id, PMT.effective_send_time AS mail_send_date,
#        CURRENT_DATE - PMT.effective_send_time AS mail_age,
#        C.id AS contract_id, C.name AS c_name, CT.id AS ct_id, CT.name AS ct_name
#   FROM contract_emails_planned_mail_template PMT
#   JOIN account_analytic_account C ON (PMT.res_id=C.id)
#   JOIN account_analytic_contract CT ON (CT.id=C.contract_template_id)
#  WHERE PMT.effective_send_time IS NOT NULL
#    AND C.date_end IS NULL
#    AND NOT EXISTS(
#        SELECT 1
#          FROM contract_emails_planned_mail_generator PMG
#         WHERE PMG.contract_id=CT.id
#           AND PMT.mail_template_id=PMG.mail_template_id
#    )
#  ORDER BY PMT.effective_send_time DESC
# ;

def migrate(cr, version):
    cr.execute("""

INSERT INTO contract_emails_planned_mail_sent AS PMS
    (contract_id, planned_mail_generator_id, send_date)

SELECT C.id, PMG.id, PMT.effective_send_time
  FROM contract_emails_planned_mail_template PMT
  JOIN account_analytic_account C ON (PMT.res_id=C.id)
  JOIN account_analytic_contract CT ON (CT.id=C.contract_template_id)
  JOIN contract_emails_planned_mail_generator PMG
       ON (PMG.contract_id=CT.id AND PMT.mail_template_id=PMG.mail_template_id)
 WHERE PMT.effective_send_time IS NOT NULL
   AND C.date_end IS NULL
    """)


    cr.execute("""
DELETE FROM ir_model_fields
WHERE model = 'contract_emails.planned_mail_template'
    """)

    cr.execute("""
DELETE FROM ir_model_constraint
WHERE model in (
    SELECT id FROM ir_model
    WHERE model = 'contract_emails.planned_mail_template'
)
    """)

    cr.execute("""
DELETE FROM ir_model_relation
WHERE model in (
    SELECT id FROM ir_model
    WHERE model = 'contract_emails.planned_mail_template'
)
    """)

    cr.execute("""
DELETE FROM ir_model
WHERE model in ('contract_emails.planned_mail_template',
                'contract_emails.planned_mail_template_object')
    """)

    cr.execute("DROP TABLE contract_emails_planned_mail_template")
