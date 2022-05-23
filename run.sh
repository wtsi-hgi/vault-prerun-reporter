#!/usr/bin/env bash

source /software/hgi/installs/vault/prerun-reporter/.venv/bin/activate

dir=`realpath $1`

bsub -o /nfs/hgi/vault/pre_reports/%J.md -e /nfs/hgi/vault/pre_reports/%J.err -G hgi -R "select[mem>3000] rusage[mem=3000]" -M 3000 "python /software/hgi/installs/vault/prerun-reporter/report.py $dir"
