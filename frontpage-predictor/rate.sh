#!/bin/bash
# usage: bash rate.sh [table] [seconds]   e.g. bash rate.sh events 120
T=${1:-events}; S=${2:-120}
a=$(ls data/raw/$T/*/part.parquet 2>/dev/null | wc -l); sleep $S
b=$(ls data/raw/$T/*/part.parquet 2>/dev/null | wc -l)
d=$((b-a)); echo "$T: $a -> $b (+$d in ${S}s), $((365-b)) remaining"
[ $d -gt 0 ] && echo "rate: $((d*60/S)) days/min, ETA ~$(( (365-b)*S/d/60 )) min"
