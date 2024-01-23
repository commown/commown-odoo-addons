#!/bin/sh

# To get results for all modules sorted by reverse completion order, use:
# po-progress.sh | sort -k 2 -n -r

pos=$*

[ -z "$pos" ] && pos=$(ls */i18n/*.po | sort)

pocount()
{
    grep -Pzo 'msgid .*\n(msgstr .*)\n' | grep -a msgid | wc -l
}

for po in $pos
do
    acount=$(msgattrib --no-fuzzy $po | pocount)
    tcount=$(msgattrib --no-fuzzy --translated $po | pocount)
    ocount=$(msgattrib --only-obsolete $po | pocount)

    echo "$po: $(printf '%2.f%%' $((100*${tcount}/${acount}))) (${tcount}/${acount} | obs: ${ocount})"

done
