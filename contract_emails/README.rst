.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
 Contract emails
=================

This module is used to plan mails to be sent during the life of a
contract. The mails are defined as mail templates that are evaluated
at the time they are sent, making it possible to take contract-life
events into account in the email text (like penalties, price changes,
...).

The emails are canceled when the contract ends.

Usage
=====

Create one or more mail template(s) with Contract as a Model field
value. Then, edit a Contract template and add one or several planned
email(s) using previously created mail template(s), and the time
interval from contract start you want each to be sent. Save the
contract template.

Then, as soon as you use this contract model to setup a new contract,
planned emails will be automatically created for you with the expected
computed date and mail template. You can access them using the
dedicated button on the contract view.


Roadmap
=======

- Automatically add a channel follower to listen to answers
