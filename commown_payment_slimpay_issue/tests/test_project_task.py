from odoo.addons.payment_slimpay_issue.tests.test_project_task import ProjectTC


def _is_module_installed(cls, module_name):
    return cls.env["ir.module.module"].search_count(
        [
            ("name", "=", module_name),
            ("state", "=", "installed"),
        ]
    )


def _setUpClass(cls):
    """If present module is loaded (e.g. in the CI), monkey patch its
    ProjectTask class to deactivate jobs as the present module uses
    them, which makes payment_slimpay_issue's tests fail without this
    monkey patch.
    """

    cls._old_setUpClass()
    if cls._is_module_installed("commown_payment_slimpay_issue"):

        cls.env = cls.env(
            context=dict(
                cls.env.context,
                test_queue_job_no_delay=True,
            )
        )


ProjectTC._is_module_installed = classmethod(_is_module_installed)
ProjectTC._old_setUpClass = ProjectTC.setUpClass
ProjectTC.setUpClass = classmethod(_setUpClass)
