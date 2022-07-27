There is no special configuration to use the module. It is however
highly customizable as the created views are designed to be easily
editable:

- webpage views


**WARNING**

Following refs are to be set before installing the module as they already exist:

- tags: tag-device-fp2 (115), tag-fp2-mod-camera (5), tag-need-screwdriver (74), tag-to-be-shipped (51)
- project: support_project (2)

.. code-block:: python

    ext_ids = [
        ('project.tags', 'tag-device-fp2', 115),
        ('project.tags', 'tag-fp2-mod-camera', 5),
        ('project.tags', 'tag-need-screwdriver', 74),
        ('project.tags', 'tag-to-be-shipped', 51),
        ('project.project', 'support_project', 2),
        ('project.task.type', 'stage_pending', 5),
        ('project.task.type', 'stage_solved', 83),
    ]

    for res_model, name, res_id in ext_ids:
        env['ir.model.data'].create({
            'module': 'commown_self_troubleshooting',
            'name': name,
            'noupdate': True,
            'model': res_model,
            'res_id': res_id,
        })
