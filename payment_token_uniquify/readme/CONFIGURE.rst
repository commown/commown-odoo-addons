The module must be set in 2 ways:

1. Define which payment tokens become obsolete

   First point is handled by a specific field on the partner called
   `uniquify_token`: we go **up** the partner tree from the new
   mandate signee; first partner with uniquify_token set to True
   defines the subtree where all mandates will be obsoleted by the new
   one.

   The action taken for obsolete tokens depends on the settings
   described in the next section.

   Note that if you want to set a default value for the
   `uniquify_token` field for new portal partners, you must set it on
   the Public Partner template of the considered website.

   For a more fine grained control, another odoo module is needed.

2. Define what to do with obsolete payment tokens

   Go to the payment acquirer's form and choose the desired behaviour:
   do nothing (the default), archive the odoo payment token or archive
   and revocate it with the payment acquirer (if implemented).
