.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================================
 Commown self-troubleshooting module
=====================================

This module is used by portal users to self-troubleshoot their
device(s).


Usage
=====

There is a link to the self-troubleshooting tool in portal users'
home. The tool guides them towards a solution to their problem by
asking them questions in a wizard-like form, which ends-up by the
creation of a ready-to-handle issue in the support project.


Configuration
=============

There is no special configuration to use the module. It is however
highly customizable as the created views are designed to be easily
editable:

- webpage views


**WARNING**

Following refs are to be set before installing the module as they already exist:
- tags: tag-device-fp2 (115), tag-fp2-mod-camera (5), tag-need-screwdriver (74), tag-to-be-shipped (51)
- project: support_project (2)

tag_defs = [
    ('project.tags', 'tag-device-fp2', 115),
    ('project.tags', 'tag-fp2-mod-camera', 5),
    ('project.tags', 'tag-need-screwdriver', 74),
    ('project.tags', 'tag-to-be-shipped', 51),
    ('project.project', 'support_project', 2),
]

for res_model, name, res_id in tag_defs:
    env['ir.model.data'].create({
        'module': 'commown_self_troubleshooting',
        'name': name,
        'noupdate': True,
        'model': res_model,
        'res_id': res_id,
    })
