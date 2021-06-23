.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================
 Contract variable discount
============================

This module is used to define variable discount on contract lines.


Usage
=====

In the contract template lines, add a discount description text. This
text is a yaml document used to describe several discounts with
following features:

- absolute or percentage discount values

- programmable start and end dates, defined by a contract reference
  date (date_start fields for instance, but may use any contract date
  defined by another module), a unit (days, weeks, months, years) and
  a value. Note that the end date is optional.

- conditionnal discounts (with extensions): base code for
  conditionnal discounts is there

For discount description sample file, see in tests/data.
