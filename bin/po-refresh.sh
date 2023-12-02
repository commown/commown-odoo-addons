#!/bin/sh

[ -z "$1" ] && echo "Please specify module(s) as arguments" && exit 1

LANGS="fr de"

for module in $@
do
    module=${module%/}

    if [ ! -f $module/__manifest__.py ]
    then
        echo
        echo "====== $module is not a module directory ======"
        echo "... skipping!"
        continue
    fi

    pot=${module}/i18n/${module}.pot

    for lang in $LANGS
    do

        echo
        echo ====== Retrieving ${lang} t10n of ${module} =====

        mkdir -p ${module}/i18n

        /usr/bin/odoo -c /etc/odoo/odoo_nosyslog.conf\
                      --log-level=critical -d odoo_commown \
                      --i18n-export=${module}.po --modules=${module} > /dev/null 2>&1

        mv ${module}.po ${pot}

        po_path=${module}/i18n/${lang}.po

        if [ -f ${po_path} ]
        then
            tmp_po=/tmp/${module}_${lang}.po
            mv ${po_path} ${tmp_po}
            msgmerge --no-fuzzy-matching --compendium ./modules_${lang}.po -o ${po_path} ${tmp_po} ${pot}
            rm ${tmp_po}
        else
            msgmerge --no-fuzzy-matching --compendium ./modules_${lang}.po -o ${po_path} /dev/null ${pot}
        fi
    done

done
