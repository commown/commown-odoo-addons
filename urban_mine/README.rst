============
 Urban mine
============

This module allows to collect anonymous registration for Commown's
urban mine offer.


Setup
=====

- set res.partner model website_form_access

- set recaptcha.key.* system parameters in
  Configuration > Parameters > System parameters

- there is an example campaign for coupons, which name must contain
  "mine urbaine"; the last created campaign matching this criterion
  will be used to generate the coupons into

- there is an example product with default_code field valued
  "urban-mine";

- check there is a colissimo account 970066 configured in keychain
