#! /bin/sh

LANGS="fr de"

cd $(git rev-parse --show-toplevel)

for lang in ${LANGS}
do
    find ./ -name ${lang}.po |\
        xargs msgcat --use-first |\
        msgattrib --translated --no-fuzzy -o ./modules_${lang}.po

    echo Written $PWD/modules_${lang}.po
done

cd - >/dev/null
