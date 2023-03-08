This module extends the functionality of the payment module which
defines the payment token model, associated to a partner.

The module adds the ability to automatically archive or delete old
payment tokens when a new one is created. The payment tokens
considered obsolete depend on the setting of the
`isolated_payment_tokens` field of the partner associated to the
token, as well as its ancestors. See the configure section for
details.
