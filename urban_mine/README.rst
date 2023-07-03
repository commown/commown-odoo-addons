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

- setup the module campaigns' names and descriptions (using their external ids)

- setup the module's product price

- setup the module's project, in particular the shipping_account_id field, for the label
  creation to work
