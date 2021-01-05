.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================
 Product rental
================

Design notes:

- as of today, a product sold on the website is associated to a
  contract template; this association make us associate a "main"
  contract product and an accessory contract product to the products
  sold on the website; the contract template also carries the
  standard commitment duration

- the real contracts are generated from the sale order using these
  configuration elements; 


This module helps creating rental contracts from rental products sold
on your website.

This module changes the product_contract module (which it relies
upon)'s behaviour in several ways:

- the number of generated contracts: one per sold rental product (and
  not one per order line like in product_contracts); the aim is to be
  able to shorten contracts individually; this should not be necessary
  in Odoo v12 anymore, as contract lines have individual start and end
  dates (among other intersting characteristics).

- the way rental product accessories are handled: with this module,
  they do not generate a contract by themselves but are associated (as
  much as possible) with the main rental product; special markers like
  ##PRODUCT## and ##ACCESSORY## can be used for that purpose in
  contract templates.

- the price structure (amount, tax) of the contract product mays be
  different to the one of the sold product; for instance, sold product
  may have an initial paid amount that corresponds to a warranty
  deposit (with no tax), but lead to rental contracts with recurring
  payments that include taxes; this is achieved using to different
  product series: the ones being sold, the ones used in the contract
  (from contract templates).

It also takes care of displaying the rental products in Odoo's
e-commerce nicely, trying to make a clear difference between the
initial payment and future recurring ones.


Setup
=====

TO BE COMPLETED

Roadmap
=======

- in v12, use the new recurring lines mecanisms to generate a single
  contract per sale order

- split this module into several modules:

  * one with the new attributes that designates rental products
  * one handling the contract generation depending on it
  * website_sale dependant code that displays initial payment and
    rental recurring amount nicely to the portal users
