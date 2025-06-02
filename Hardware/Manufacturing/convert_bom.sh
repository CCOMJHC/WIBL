#!/bin/zsh

echo "Qty\tDesignator\tFootprint\tComment\tLCSC Part #\tDescription" > $2

cat $1 | cut -d';' -f 1-2,4-6 | tr ';' '\t' | tr -d '\"' | awk -F '\t' 'NR > 1 {printf("%d\t%s\t%s\t%s\t\t%s\n",$1,$4,$3,$2,$5);}' >> $2

exit 0
