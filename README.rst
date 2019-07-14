.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================================
 Account invoice merge auto pay
================================

This module completes the `account_invoice_merge_auto` module by
paying the invoices automatically once all invoice merge candidates
have been handled, have they finally been merged or not.

It uses the `queue_job_suscribe` module so that payments are performed
in their own database transaction: if one payment crashes for any
reason, the others are not affected and an administrator can be
notified (see Configuration below).


Usage
=====

See `account_invoice_merge` module usage: no further usage
instructions apply to this module.


Configuration
=============

There is no configuration specific to this module, however following
parameters fit usually well together:

- Configure the `queue_job` module: define a user to be a job manager
  (in the `Configuration > Users` section) and to be notified in case
  of a failed job (`Configuration > Users > Connectors`)

- Also configure Odoo for `queue_job` of course: do not forget to add
  `queue_job` to the `server_wide_modules` option and to set `workers`
  to a suitable value (at least >= 1).

- Adjust the `Automatically merge invoices` cron task execution hour
  to your liking; for instance, if you use the `contract` module to
  generate the draft invoices to be merged and pay, set their cron
  tasks hours to execute the `contract` cron before the
  `account_invoice_merge` one.
