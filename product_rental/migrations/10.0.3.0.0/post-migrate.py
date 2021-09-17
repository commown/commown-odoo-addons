# coding: utf-8
#
# Could check:
# - product contract template vs. contract template
# - product price (choice may be wrong within same contractual category)
#

import logging

from openerp import SUPERUSER_ID
from openerp.api import Environment


_logger = logging.getLogger(__name__)
# _logger.setLevel(int( (logging.DEBUG + logging.INFO) / 2.))
_logger.setLevel(logging.INFO)


ignored_sales = {  # XXX must be emptied! DONE :-)
}


explicit_links = {  # <so_line id>: <contract line id>
    939: 1078,  # SO00749 (Option FP Lineage OS)
    1403: 616,  # SO01116 (Asus GeForce GTX 1070 STRIX - 8 Go)
    1587: 1405, # SO01262 (Installation de Fairphone Open et applis libres)
    1700: 1277, # SO01345 (Installation de Fairphone Open et applis libres)
    2128: 1338, # SO01630
    2431: 944,  # SO01809 (Module batterie supplémentaire)
    2584: 3074, # SO01916 (Power pack)
    2738: 1049, # SO02023 (FP Open)
    1205: 373,  # SO00964 Écran pour ordi Elie
    1206: 373,  # SO00964 Clavier pour ordi Elie
    514: 1388,  # SO380 OPEN OS
    497: (
        615,    # SO368 Batterie FP2 suppl
        887,    # SO368 OPEN OS
    ),
    3244: 1360, # SO01728-02 (SO01728-01 was canceled)
    1926: 722,  # XXX Sold product is a contract product (clavier MK120)
    5611: (     # SO02277 (Koncepterie): Nager-IT manually added afterwards
        1636,
        1637,
        1638,   # 1 per computer but 1!
        1639,
        1640
    ),
    # SO03559
    5002: (3507, 3510),   # EULER-M-H370 PRO
    5004: (3514, 3522),   # Clavier et souris filaire Logitech PRO
    5005: (3517, 3523),   # Écran PRO 24,5'' IIYAMA G-Master G2530HSU-B1
    5138: 3513,
    # SO03348
    4619: 3251,           # Fairphone 3 Services Premium PRO
    4620: (3254, 3257),   # why N131ZU PRO - 13,3" - Le Poids Plume
    4621: (3260, 3263),   # EULER-M-H370 PRO - Le fanless puissant par PCVERT
    4622: 3264,           # Écran PRO 24,5'' IIYAMA G-Master G2530HSU-B1
    # SO02580
    3595: (1724, 1649,
           1727, 1733,    # 6 x why N131ZU PRO - 13,3" - Le Poids Plume
           1736, 1738),
    3596: 1730,           # 1 x EULER-M-H270K PRO - Le fanless puissant par PCVERT
    3594: (1726, 1678,
           1729, 1732,    # 7 x Écran PRO 24,5'' IIYAMA G-Master G2530HSU-B1
           1735, 1737,
           1739),
    3877: (1725, 1675,
           1728),         # 3 x Souris équitable PRO par Nager-IT
    # SO02505
    3488: (1480, 1483),   # 2 x why N131ZU PRO - 13,3" - Le Poids Plume
    3489: (1486, 1489),   # 2 x EULER-M-H270K PRO - Le fanless puissant par PCVERT
    3490: (1493, 1496),   # 2 x Écran PRO 24,5'' IIYAMA G-Master G2530HSU-B1
    3491: (1495, 1497),   # 2 x Clavier et souris filaire Logitech PRO
    3566: (1490, 1491),   # 2 x Crosscall Core-X3 PRO
    # SO02129
    2912: (1195, 1198), # 2 x Pour Devis - Location mensuelle Ordinateur B2B => N650
    2913: (1201, 1204), # 2 x Pour Devis - Location mensuelle Ordinateur B2B => EULER
    2916: (1207, 1205), # (1+2) x [Contrats] Location mensuelle - PC - Composant supplémentaire => Écrans
    2917: 1206,         # 1 x [Contrats] Location mensuelle - PC - Composant supplémentaire => clavier + souris
    # SO02288
    3176: 1318,         # Location mensuelle Ordinateur B2B / Location d'un écran : Ecran IIYAMA Prolite E
    # SO02103
    2863: 1110,         # PC - Composant supplémentaire / Location d'un accessoire : Écran IIYAMA G-Master
    # SO01799
    2416: 934,          # Location mensuelle Ordinateur B2B / Location d'un Clavier et souris filaire
    2417: 933,          # Location mensuelle Ordinateur B2B / Location d'un Écran IIYAMA
    # SO03935
    5504: 4210,         # Souris équitable par Nager-IT / [Contrats] Location mensuelle PC : Souris Nager IT
    5506: 4115,         # DAY - Casque GS filaire (location annuelle) / Location DAY - Casque GS
}

ignored_sold_products_in_checks = {
    156,     # Installation de Fairphone Open et applis libres
    217,     # FP2 - En route pour LineageOS !
}

ignored_order_lines = {
    3723,              # SO02674 Changement option FP3 Premium
    2599,              # SO01915 "Option DéGAFAMisation" XXX useless?
    2290,              # SO01728 Mickael W: canceled FP2
}

ignored_contract_product_in_checks = {
    10188,  # Remise "Crosscall Année 3"
    9516,   # Transition FP2->FP3
    8216,   # Remise "Bonus Soin au FP2"
    8217,   # Fan de durabilité FP2
    3474,   # Pénalités Dégradation coque
    1923,   # Pénalités Vol/Perte/Dégradation
    2282,   # Remise - geste commercial sur mensualités Ordinateur
    148,    # Remise - geste commercial sur mensualités FP
    61,     # Remise "Tarif préférentiel 2017 FP2
    2238,   # Licence Windows 10 Pro
}

product_sale_contract = {

    166: (      # Crosscall Core-X3
        3734,   # [Contrats] Location mensuelle Crosscall (SO03140)
        2653,   # Location mensuelle Crosscall BtoB (SO02302) XXX (why different?)
    ),
    179: (      # Crosscall Trekker X4
        2653,   # Location mensuelle Crosscall Trekker X4
        3734,   # [Contrats] Location mensuelle Crosscall XXX (why different?)
        ),
    228: 3734,  # Crosscall Tablette Core-T4 / [Contrats] Location mensuelle Crosscall
    234: 10454, # Location mensuelle Crosscall Core-X4 / [Contrats] Location mensuelle Crosscall BtoC

    141: 3736,  # PP / [Contrats] Location mensuelle Pavé Parisien

    9: 63,      # why! N131WU / Location mensuelle PC BtoC
    10: 63,     # why! N650DU basic 2017 / Location mensuelle PC BtoC
    11: 63,     # why! N240JU basic 2017 / Location mensuelle PC BtoC
    12: 63,     # why! N650DU puissant 2017 / Location mensuelle PC BtoC
    13: 63,     # why! P775DM3 2017 / Location mensuelle PC BtoC
    14: 63,     # M² Asus Zenbook (Ubuntu) - 2017 / Location mensuelle PC BtoC
    15: 63,     # M² Asus Zenbook stockage min (2017) / Location mensuelle PC BtoC
    18: 63,     # M² Asus Zenbook (Windows) - 2017 / Location mensuelle PC BtoC
    25: 63,     # M² Asus Pro (Ubuntu) - 2017 / Location mensuelle PC BtoC
    31: 63,     # EULER-M-H110 / Location mensuelle PC BtoC
    34: 63,     # EULER-MX-H270 / Location mensuelle PC BtoC
    35: 63,     # H500P-Z370 / Location mensuelle PC BtoC
    192: 63,    # H500P-Z390 / Location mensuelle PC BtoC
    41:  63,    # N131WU / Location mensuelle PC BtoC
    42: 63,     # N650 / Location mensuelle PC BtoC
    43: 63,     # Monstre / Location mensuelle PC BtoC
    158: 3733,  # why P775DM3 PRO - 17,3" - Le Monstre / [Contrats] Location mensuelle PC
    44: 63,     # why N240JU - 14" - L'Abordable / Location mensuelle PC BtoC
    49: 63,     # Silencio par PCVERT (pour HF Conseil) / Location mensuelle PC BtoC
    54: (       # why N650DU - 15,6" - Le Couteau-Suisse (B2B)
        3733,   # [Contrats] Location mensuelle PC (SO02162)
        1926,   # Location mensuelle PC BtoB XXX (why different?)
    ),
    58: 63,     # M² Asus Zenbook (Windows) - 2017 / Location mensuelle PC BtoC
    64: 1926,   # Location d'un ordinateur : Asus Pro Full HD 2018 (B2B) / Location mensuelle FP2 BtoB
    120: 1926,  # Pour Devis - Location mensuelle Ordinateur B2B / Location mensuelle PC BtoB
    132: 63,    # Asus Pro Full HD par M² (v2018) / Location mensuelle PC BtoC
    147: 63,    # M² Asus Pro (Ubuntu) - 2017 / Location mensuelle PC BtoC
    29: 63,     # M² Asus ROG Strix - 2017 / Location mensuelle PC BtoC
    156: 3733,  # N131ZU PRO / [Contrats] Location mensuelle PC
    159: 3733,  # N650 PRO / [Contrats] Location mensuelle PC
    160: 3733,  # EULER-M-H110 PRO / [Contrats] Location mensuelle PC
    161: 3733,  # EULER-M-H270K PRO / [Contrats] Location mensuelle PC
    165: 63,    # Plume / Location mensuelle PC BtoC
    167: 63,    # EULER-M-H270 / Location mensuelle PC BtoC
    189: 63,    # N240WU / Location mensuelle PC BtoC
    191: 3733,  # N240WU PRO / [Contrats] Location mensuelle PC
    197: 63,    # EULER-MX-H270 / Location mensuelle PC BtoC
    206: 63,    # EULER-M-H370 / Location mensuelle PC BtoC
    207: (      # EULER-M-H370 PRO
        3507,   # EULER-M-H370 PRO
        3733,   # [Contrats] Location mensuelle PC XXX (why different?)
    ),

    36: 63,     # Écran IIYAMA G-Master GE2488HS-B2 / Location mensuelle PC BtoC
    37: 63,     # Écran IIYAMA PROLITE E2283HS-B1 / Location mensuelle PC BtoC
    38: 63,     # Clavier et souris filaire Logitech / Location mensuelle PC BtoC
    168: 63,    # Écran 22'' IIYAMA PROLITE E2283HS-B3 / Location mensuelle PC BtoC
    169: 63,    # Écran 24,5'' IIYAMA G-Master G2530HSU-B1 / Location mensuelle PC BtoC
    171: 3733,  # Écran PRO 24,5'' IIYAMA G-Master G2530HSU-B1 / [Contrats] Location mensuelle PC
    172: 3733,  # Écran PRO 22'' IIYAMA PROLITE E2283HS-B3 / [Contrats] Location mensuelle PC
    173: 3733,  # Clavier et souris filaire Logitech PRO / [Contrats] Location mensuelle PC
    190: 3733,  # Écran PRO 27'' IIYAMA Prolite XB2783HSU-B3 / [Contrats] Location mensuelle PC
    200: 63,    # Souris équitable par Nager-IT / Location mensuelle PC BtoC
    201: 3733,  # Souris équitable PRO par Nager-IT / [Contrats] Location mensuelle PC
    210: 63,    # Écran IIYAMA G-Master GB2530HSU-B1 / Location mensuelle PC BtoC

    1:  60,     # Formule Premium / Location mensuelle FP2 Premium BtoC
    3: (        # Formule Héros Ordinaire
        59,     # Location mensuelle FP2 Héros ordinaire BtoC
        60,     # Location mensuelle FP2 Premium BtoC
    ),
    24: 59,     # Formule Héros Ordinaire / Location mensuelle FP2 Héros ordinaire BtoC
    27: 60,     # Formule Premium / Location mensuelle FP2 Premium BtoC
    30: 1925,   # Installation de Fairphone Open et applis libres / Location mensuelle FP2 BtoB
    47: 1925,   # XXX Location mensuelle FP2 BtoB / Location mensuelle FP2 BtoB
    48: 1926,   # XXX Location mensuelle FP2 BtoB / Location mensuelle FP2 BtoB
    66: 60,     # Formule Premium / Location mensuelle FP2 Premium BtoC
    67: (       # Formule Héros Ordinaire
        59,     # Location mensuelle FP2 Héros ordinaire BtoC
        60,     # Location mensuelle FP2 Premium BtoC (SO01630 change HO > Premium)
    ),
    129: 60,    # Formule Premium / Location mensuelle FP2 Premium BtoC
    130: (      # Formule Héros Ordinaire
        59,     # Location mensuelle FP2 Héros ordinaire BtoC
        60,     # Passage en Location mensuelle FP2 Premium BtoC (SO02199)
    ),
    182: 5665,  # Formule Premium sans engagement / Location mensuelle FP2 Premium sans engagement BtoC
    193: 5667,  # Fairphone 3 Services Premium / [Contrats] Location mensuelle FP3 Premium BtoC
    194: 5667,  # Câble chargement FP3 (USB-A vers USB-C) / [Contrats] Location mensuelle FP3 Premium BtoC
    195: 5667,  # Chargeur FP3 / [Contrats] Location mensuelle FP3 Premium BtoC
    196: 6434,  # FP3 PRO / [Contrats] Location mensuelle FP3 Premium B2B
    203: 6434,  # Chargeur FP3 PRO / [Contrats] Location mensuelle FP3 Premium B2B
    204: 6434,  # Chargeur FP3 PRO / [Contrats] Location mensuelle FP3 Premium B2B

    230: 10442, # BOSS - Casque GS bluetooth (location mensuelle) / [Contrats] Location GS BtoC
    236: 10442, # BOSS - Casque GS bluetooth (location annuelle) / [Contrats] Location GS BtoC
    237: 10442, # DAY - Casque GS bluetooth (location mensuelle) / [Contrats] Location GS BtoC
    238: 10442, # DAY - Casque GS filaire (location annuelle) / [Contrats] Location GS BtoC

}


def so_line_name(so_line):
    if not so_line:
        return False
    return u'%s-%d' % (so_line.order_id.name, so_line_index(so_line))


def so_line_index(so_line):
    return 1 + so_line.order_id.order_line.ids.index(so_line.id)


def get_contract_products(contracts, so_line):
    pt = so_line.product_id.product_tmpl_id
    try:
        products = product_sale_contract[pt.id]
        if isinstance(products, int):
            products = (products,)
        return products
    except KeyError:
        _logger.error(u'Not found: %s (%d)', pt.name, pt.id)
        for iline in contracts.mapped('recurring_invoice_line_ids'):
            _logger.error(
                u'Contract line %s, product: %s (%d)',
                iline.name, iline.product_id.name, iline.product_id.id)
        return ()


def check_sales_contract_numbers(env):
    contract_model = env['account.analytic.account']
    for sale in env['sale.order'].search([('state', '=', 'sale')]):
        count = 0
        for ol in sale.order_line:
            if ol.product_id.is_contract:
                count += int(ol.product_uom_qty)
        if count == 0:
            continue
        last_contract = contract_model.search([
            ('name', '=like', '%s-%02d%%' % (sale.name, count)),
        ])
        if len(last_contract) != 1:
            _logger.error(
                u'Wrong contract number %d for sale %s (expected: %d)',
                len(contract_model.search([
                    ('name', '=like', sale.name + u'-%')
                ])), sale.name, count)


def print_complex_sales(env):

    contract_names = set(env['account.analytic.account'].search([
        ('name', '=like', 'SO%'),
    ]).mapped('name'))
    sales_contract_count = {}
    for cn in contract_names:
        cn = cn.split('-')[0]
        sales_contract_count.setdefault(cn, 0)
        sales_contract_count[cn] += 1

    so_ids = [int(so_name[2:])
              for so_name, count in sales_contract_count.iteritems()
              if count > 1]
    sales = env['sale.order'].search([('id', 'in', so_ids)])

    complex_sales = sales.filtered(lambda so: set(
        so.order_line.mapped('product_uom_qty')) - {1.0})
    for so in complex_sales:
        print_complex_sale(so)


def print_complex_sale(so, skip=0, length=75):
    env = so.env
    print u'\n' + so.name
    print u' * SALE:\n  - ' + u'\n  - '.join(
        '%d->%s: %d x %s' % (ol.id, ol.contract_id.name, ol.product_uom_qty, ol.product_id.name)
        for ol in so.order_line)
    cs = env['account.analytic.account'].search([
        ('name', '=like', so.name + '-%'),
        ('recurring_invoices', '=', True),
    ])
    print u' * CONTRACTS:'
    for c in cs:
        print u'    - %s (%d)\n      +' % (c.name, c.id),
        print u'\n      + '.join(
            u'%d->%s: %s' % (l.id, so_line_name(l.sale_order_line_id),
                             l.name.replace(u'\n', u' ')[skip:skip + length])
            for l in c.recurring_invoice_line_ids)


def link_sales_and_contracts(env):
    sales = env['sale.order'].search([
        ('order_line.product_id.product_tmpl_id.contract_template_id',
         '!=', False),
        ('state', '=', 'sale'),
        ('id', 'not in', tuple(ignored_sales)),
    ], order='id DESC')

    iline_model = env['account.analytic.invoice.line']

    for sale in sales:
        count = 0
        contracts = env['account.analytic.account']

        for so_line_num, so_line in enumerate(sale.order_line):

            if so_line.id in ignored_order_lines:
                _logger.info(
                    '[LINK] Ignoring order line %d.', so_line.id)
                continue

            product = so_line.product_id
            if product.is_rental:

                # Early customers coming from WP had qty=0 but client_order_ref
                # set (to their WP ref)
                qty = int(so_line.product_uom_qty)
                if qty == 0:
                    if sale.client_order_ref:
                        qty = 1
                    else:
                        _logger.info(
                            u'%s/%d has 0 qty (prod id %d): %s', sale.name,
                            so_line_num, product.product_tmpl_id.id,
                            product.product_tmpl_id.name)

                if so_line.id in explicit_links:
                    iline_ids = explicit_links[so_line.id]
                    if isinstance(iline_ids, int):
                        iline_ids = [iline_ids]
                    for iline_id in iline_ids:
                        iline = iline_model.browse(iline_id)
                        if not iline.sale_order_line_id:
                            iline.sale_order_line_id = so_line.id
                        if not so_line.contract_id:
                            so_line.contract_id = iline.analytic_account_id.id

                # Skip already linked lines but set count (for idempotency)
                if so_line.contract_id:
                    _logger.debug('%s already linked to contract %s',
                                  so_line_name(so_line), so_line.contract_id.name)
                    count += qty
                    continue

                for _pnum in range(int(qty)):
                    if product.is_contract:
                        count += 1

                    contract = env['account.analytic.account'].search([
                        ('name', '=like', '%s-%02d%%' % (
                            sale.name, max(count, 1))),
                    ])
                    if len(contract) != 1:
                        _logger.error(u'Could not find contract named %s-%02d',
                                      sale.name, max(count, 1))
                        continue
                    contracts |= contract
                    pcontract_tpl = product.product_tmpl_id.contract_template_id
                    if (product.is_contract
                            and pcontract_tpl != contract.contract_template_id
                            and not sale.client_order_ref):
                        _logger.error(
                            u'%s: product contract %s mismatch w/ contract %s',
                            sale.name, pcontract_tpl.name,
                            contract.contract_template_id.name
                            )
                    assign_by_contract_product(so_line, contract)

        check_sale_complete(sale)
        check_contracts_complete(contracts)


def assign_by_contract_product(so_line, contracts):
    _logger.debug('Considering so_line %s, contracts %s',
                  so_line_name(so_line), u' - '.join(contracts.mapped('name')))
    contract_product_ids = get_contract_products(contracts, so_line)

    for iline_num, iline in enumerate(
            contracts.mapped('recurring_invoice_line_ids'), 1):
        if iline.sale_order_line_id:
            if so_line.id not in explicit_links:
                _logger.info('Already attributed contract line %s (%s)',
                             iline.id, iline.analytic_account_id.name)
            continue
        if iline.product_id.id in contract_product_ids:
            _logger.debug('Assign contract line %d', iline.id)
            iline.sale_order_line_id = so_line.id
            if not so_line.contract_id:
                so_line.contract_id = iline.analytic_account_id.id
                _logger.debug('LINKED %s/%d with line %s',
                              so_line.contract_id.name, iline_num,
                              so_line_name(so_line))
            break
    else:
        if so_line.id not in explicit_links:
            contract_lines = contracts.mapped('recurring_invoice_line_ids')
            _logger.warning(
                (u'%s: Sold product "%s" (%d - description "%r") not found'
                 u' in contracts. Was searching:\n- %s\n'
                 u' In:\n- %s'),
                so_line.order_id.name,
                so_line.product_id.product_tmpl_id.name,
                so_line.product_id.product_tmpl_id.id,
                so_line.name,
                str(contract_product_ids),
                u'\n- '.join(u'sale: "%s" (%d) - contract linked: %s' % (
                    l.product_id.name, l.product_id.id,
                    bool(l.sale_order_line_id)) for l in contract_lines),
            )


def check_contracts_complete(contracts):
    for iline_num, iline in enumerate(
            contracts.mapped('recurring_invoice_line_ids'), 1):
        if iline.product_id.id in ignored_contract_product_in_checks:
            continue
        if not iline.sale_order_line_id:
            product = iline.product_id
            _logger.warning(
                'No order linked for contract %s/%d (%s"), product "%s" (%d)',
                iline.analytic_account_id.name, iline_num, iline.name,
                product.name, product.id)


def check_sale_complete(sale):
    for so_line in sale.order_line:
        if not so_line.product_id.is_rental or (
                not so_line.product_uom_qty and not sale.client_order_ref):
            continue
        if so_line.product_id in ignored_sold_products_in_checks:
            _logger.debug(
                '[CHECK] Ignoring order line %d sold product "%s" (%d)',
                so_line.id, so_line.product_id.name, so_line.product_id)
            continue
        if so_line.id in ignored_order_lines:
            _logger.debug('[CHECK] Ignoring order line %d.', so_line.id)
            continue
        if not so_line.contract_id:
            _logger.error(
                ('[CHECK] No link to contract for so_line %s,'
                 ' product name "%s" (%d)'),
                so_line_name(so_line), so_line.product_id.name,
                so_line.product_id.product_tmpl_id.id)


def fix_mail_templates(env):
    for mt in env['mail.template'].search([('body_html', 'like', 'rental_contract_tmpl_id')]):
        mt.body_html = mt.body_html.replace(
            u'rental_contract_tmpl_id', u'contract_template_id')


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    link_sales_and_contracts(env)
    fix_mail_templates(env)
