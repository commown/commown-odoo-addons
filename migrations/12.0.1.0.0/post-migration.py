import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def _rename_contract_template_commitment_info(env):
    _logger.info("Rename contract template commitment info")
    for template in env['contract.template'].search([]):
        template.commitment_duration = template.min_contract_duration


def _move_contract_commitment_info_to_line(env):
    _logger.info("Move contract commitment info to line level")
    for contract in env['contract.contract'].search([]):
        for line in contract.contract_line_ids:
            line.commitment_end_date = contract.min_contract_end_date
            line.commitment_duration = contract.min_contract_duration


@openupgrade.migrate()
def migrate(env, version):
    _logger.info("Post-migration 12.0.1.0.0")
    _rename_contract_template_commitment_info(env)
    _move_contract_commitment_info_to_line(env)
