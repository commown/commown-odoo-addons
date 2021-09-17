def migrate(cr, version):
    cr.execute('UPDATE product_template'
               ' SET contract_template_id=rental_contract_tmpl_id,'
               '     is_contract=(rental_contract_tmpl_id IS NOT NULL)')
