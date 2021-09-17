.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======================================
 Commown contractual issues management
=======================================

This module is used to manage contractual issues at Commown (losses,
breakages, thefts). Some contractual clauses may indeed require to
track them (e.g. when only one breakage per year is at Commown's
charge).

A contractual issue is a project issue that is related to a rental
contract. It has some dedicated attributes:

- `contract_id`: the rental contract the broken device was attached to

- `contractual_issue_date`: the date when the breakage occurred

- `contractual_issue_type`: the type of contractual issue (loss,
  breakage, theft)

- `penalty_exemption`: true if present issue will not be counted as a
  contractual issue, e.g.: the customer decided to pay or Commown
  commercial initiative.
