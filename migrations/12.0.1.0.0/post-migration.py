import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def _rename_contract_template_commitment_info(env):
    _logger.info("Rename contract template commitment info")
    openupgrade.logged_query(
        env.cr, """
        UPDATE contract_template_line CTL
        SET commitment_duration = CT.min_contract_duration
        FROM contract_template CT
        WHERE CT.id = CTL.contract_id
        """)

    for template in env['contract.template'].search([]):
        template.commitment_duration = template.min_contract_duration


def _move_contract_commitment_info_to_line(env):
    _logger.info("Move contract commitment info to line level")
    openupgrade.logged_query(
        env.cr, """
        UPDATE contract_line CL
        SET
          commitment_end_date = CC.min_contract_end_date,
          commitment_duration = CC.min_contract_duration
        FROM contract_contract CC
        WHERE CC.id = CL.contract_id
        """)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info("Post-migration 12.0.1.0.0")
    _rename_contract_template_commitment_info(env)
    _move_contract_commitment_info_to_line(env)
