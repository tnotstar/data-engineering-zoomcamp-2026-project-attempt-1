#!/bin/bash
# =============================================================
# Build-time helper — Stage 1 (Silver): VCF → TSV
# Runs inside the Docker multi-stage build, NOT at container runtime.
# =============================================================
set -e

mkdir -p /data/silver

echo "Generating Silver layer: extracting population frequencies from VCF..."

samples=$(bcftools query -l /data/raw/freq-subset.vcf.gz | tr '\n' '\t')
echo -e "variant_id\tCHROM\tpos\tref\talt\t$samples" > /data/silver/variantes_poblaciones.tsv

bcftools query \
    -f '%ID\t%CHROM\t%POS\t%REF\t%ALT[\t%AC\t%AN]\n' \
    /data/raw/freq-subset.vcf.gz | \
awk 'BEGIN {FS="\t"; OFS="\t"} {
    for (i=6; i<=NF; i+=2) {
        ac = $i; an = $(i+1);
        if (an != "." && an > 0 && ac != ".") {
            $i = ac/an;
        } else {
            $i = "NULL";
        }
    }
    print $1,$2,$3,$4,$5,$6,$8,$10,$12,$14,$16,$18,$20,$22,$24,$26,$28
}' >> /data/silver/variantes_poblaciones.tsv

echo "Silver layer complete: $(wc -l < /data/silver/variantes_poblaciones.tsv) lines in TSV."
