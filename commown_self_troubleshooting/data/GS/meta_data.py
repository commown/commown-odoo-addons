{
  "contract_domain": base_domain + [
      ("contract_template_id.name", "like", "GS%"),
      ("contract_line_ids.sale_order_line_id.name", "ilike", "%day%"),
  ],
}
