.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======================
 Payment Slimpay issue
=======================

This module helps handling Slimpay payment issues using a dedicated
project dashboard.


Setup
=====

Once the module is installed, you probably want to review:

- The product that prices the payment management fees: name, price,
  taxes, income account

  This product will be added to your customer invoices whose Slimpay
  payment was rejected, if the number of payment retrials has become
  bigger than `payment_slimpay_issue.invoice_fee_after_trial_number`
  if set (1 by default: first payment issue is free, second will be
  charged). It **must** have Invoicing data set, particularly the
  `property_account_income_id` (Income account) field.

  These fees are different from bank fees that some banks (e.g. german
  bank N26) also invoice to the company, which are systematically
  added (see below).

- The product that prices the payment bank fees: name, taxes, income
  account (**mandatory**); these fees are automatically added to the
  invoice, the price being the difference between the rejected amount
  of the Slimpay issue and the total amount of the invoice.

- The project dashboard that handles the payment issues. You can
  rename the existing columns and add new ones to suit your needs, but
  the functionnalities dedicated to each original stage are not meant
  to be changed in any way.

- The frequency of the crontab that checks Slimpay API for new payment
  issues.

- The template of the mail sent to your customers when they have
  payment issue (search "rejected payment" in odoo's mail template
  list).

Note that if you delete the above-mentionned products, the issue
handling process should still work and the invoice will not be added
the fees. The product will not be recreated on module update, as this
behaviour is supposed to be done on purpose by the user (you).

You may also want to customize following system parameters:

- payment_slimpay_issue.payment_retry_after_days_number: the number of
  days to wait before attempting a new payment when a task enters the
  stage_warn_partner_and_wait column

- payment_slimpay_issue.management_fees_after_retrial_number: the
  number of payment issues without extra management fees invoiced to
  your customer

- payment_slimpay_issue.max_retrials: the number of payment retrials
  after which no more automatic mecanism handles the issue (e.g. you
  prefer calling your customer)

As stated above, by default invoices can be added fees (unless you set
a very big value for the
`payment_slimpay_issue.invoice_fee_after_trial_number` system
parameter), so the journal of these invoices must be set to allow
cancelling entries (`update_posted = True`).

Payment issue detection uses Slimpay's dedicated programming interface
(API) that is also used for mandate signature in the payment_slimpay
module. So if payment works, present module should work too without
extra settings.

Documentation
=============

The module regularly checks with Slimpay for payment issues (every 8
hours by default), and creates a task in the dedicated project
(called "Slimpay payment issues tracking" by default).

If the task cannot be related to an invoice, it ends-up in the "No
corresponding invoice found", and no further automatic action will
occur. This happens when the Slimpay payment reference does not match
the reference of a payment transaction in your odoo database.

In the opposite case, the task will be related to the invoice and an
issue payment counter incremented for that invoice (stored in the
task, and displayed on it in the dashboard).

The module will then automatically emit a warning email to the
partner, stating that a new payment trial will occur 3 calendar days
later. The task then stays in the "Warn partner then wait" for 3
days. When this delay expires, it is automatically moved to the "Retry
payment and wait" column, where a new SEPA order is sent to Slimpay,
and wait there for 8 more calendar days. If no other payment issue is
raised after this period, the issue is considered fixed and the task moved in
the corresponding column. Otherwise this warning-wait-pay-wait cycle
is performed again, in the limit of a maximum (2 by default), where
the task is moved to the "Max payment trials reached" column, for
manual handling (an email is then sent to the company's email by
default).

Testing (developers)
====================

It may be difficult to test the effect of a payment issue as it is not
straightforward to trigger one on Slimpay testing infrastructure (see
https://dev.slimpay.com/hapi/guide/payments/handle-payment-issues).

Of course you can execute the unit tests to simulate such a event, but
it may be useful to see the result in the web interface. To achieve
this, a script like this can be executed in a shell, given an unpaid
invoice `invoice`::

  # If you want to reuse an existing payment issue instead of creating a new
  # one, just get it using ``env['project.task'].browse``:
  task = env['project.task'].create({
      'name': u'Test rejected payment',
      'invoice_id': invoice.id,
      'partner_id': invoice.partner_id.id,
      'project_id': env.ref('payment_slimpay_issue.project_payment_issue').id,
      'slimpay_payment_label': u'Test payment label',
  })
  task._slimpay_payment_issue_get_or_create = lambda *args: task
  task._slimpay_payment_issue_handle(
      task.project_id,
      None,
      {'rejectAmount': task.invoice_id.amount_total + 5.,
       'dateCreated': u'2020-01-01T00:00'},
      task._slimpay_payment_invoice_prefix()
  )


Roadmap
=======

See what parameter is required to fit some others' needs and
generalize this module so that it becomes an (optional) companion of
the `payment_slimpay` module.
