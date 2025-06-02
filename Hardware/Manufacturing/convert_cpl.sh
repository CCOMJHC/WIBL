#!/bin/zsh

echo "Designator,Mid X,Mid Y,Layer,Rotation" >$2
cat $1 | tr -s ' ' ' ' | cut -d' ' -f1-4 | awk '{printf("%s,%.2lf,%.2lf,Top,%d\n",$1,$2,$3,$4);}' >>$2

exit 0
