.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================================
 Project issue last partner message date
=========================================

This module adds a computed field to project issues to store the date
of the last message of the issue's partner (email or comment). If no
message was sent by the partner, the issue's creation date is used.

This field is then used to sort issues (by ascending date). It is also
displayed on the kanban view.
