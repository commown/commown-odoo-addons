The module must be set in 2 ways:

1. Define which payment tokens become obsolete

   First point is handled by a specific field on the partner called
   `isolated_payment_tokens`: we go **up** the partner tree from the
   new mandate signee; first partner without a parent or with a parent
   which `isolated_payment_token` field is set to True defines the
   subtree where all mandates will be obsoleted by the new one.

   The action taken for obsolete tokens depends on the settings
   described in the next section.

2. Define what to do with obsolete payment tokens

   Go to the payment acquirer's form and choose the desired behaviour:
   do nothing (the default), archive the odoo payment token or archive
   and revocate it with the payment acquirer (if implemented).
