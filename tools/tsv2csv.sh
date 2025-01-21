#!/bin/sh
awk -F'\t' -v OFS=',' '
{
    for (i=1; i<=NF; i++) {
        # Trim leading/trailing spaces
        gsub(/^ +| +$/, "", $i)
        # Quote fields with commas or spaces
        if ($i ~ /,/) {
            $i = "\"" $i "\""
        }
    }
    print
}' "$1"
