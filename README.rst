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

- fix or percent discount values

- programmable start and end dates, defined by a contract reference
  date (date_start fields for instance, but may use any contract date
  defined by another module), a unit (days, weeks, months, years) and
  a value. Note that the end date is optional.

- conditionnal discounts (with extensions): base code for
  conditionnal discounts is there


Anatomy of a discount formula
=============================

A discount formula is a succession of one or more discount
descriptions in the yaml format, and more precisely of the following
form ('[]' surround optional parts)::

  Name of the discount:

    [condition: <name of a condition (none present in current module); e.g: no_issue_to_date>]

    amount:
      value: <a decimal number>
      type: fix|percent

    start:
      reference: <a date contract attribute name, for instance: date_start>
      value: <an integer value>
      unit: days|weeks|months|years

    [end:
      reference: <a date contract attribute name, for instance: date_start>
      value: <an integer value>
      unit: days|weeks|months|years]

Example::

  Discount for taking care of your device:

    condition: no_issue_to_date

    amount:
      value: 10
      type: percent

    start:
      reference: date_start
      value: 13
      unit: months

  Discount for being a so loyal customer:

    amount:
      value: 50
      type: percent

    start:
      reference: date_start
      value: 4
      unit: years
