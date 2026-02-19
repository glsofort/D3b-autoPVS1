#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# author: Jiguang Peng
# created: 2019/6/27
# modified: 2021/6/29
# modified: 2022/10/04
# mod_author: Miguel Brown

import os
import configparser
from pyfaidx import Fasta
from pyhgvs.utils import read_transcripts
from utils import read_morbidmap, read_pathogenic_site, read_pvs1_levels, create_bed_dict, read_gene_alias


BinPath = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser()
config.read(BinPath+'/config.ini')

for top in config:
    for key in config[top]:
        if key == 'genome':
            continue  # Genome files provided externally at runtime
        if not config[top][key].startswith('/'):
            config[top][key] = os.path.join(BinPath, config[top][key])

pvs1_levels = read_pvs1_levels(config['DEFAULT']['pvs1levels'])

gene_alias = read_gene_alias(config['DEFAULT']['gene_alias'])

gene_trans = {}
trans_gene = {}
with open(config['DEFAULT']['gene_trans']) as f:
    for line in f:
        record = line.strip().split("\t")
        gene, trans = record[0], record[1]
        gene_trans[gene] = trans
        trans_gene[trans] = gene

# Lazy loading: only load build-specific data when requested
_build_cache = {}

def get_build_data(build):
    """Load and cache build-specific resources (genome, transcripts, domains, etc.).

    The genome FASTA is resolved from the current working directory (caller stages it there),
    while all other data files resolve from the script's install directory via config.ini.
    """
    build = build.upper()
    if build not in _build_cache:
        # Genome FASTA: resolve from cwd if relative (Nextflow stages it in work dir)
        genome_path = config[build]['genome']
        if not os.path.isabs(genome_path):
            genome_path = os.path.join(os.getcwd(), genome_path)

        _build_cache[build] = {
            'genome': Fasta(genome_path),
            'transcripts': read_transcripts(open(config[build]['transcript'])),
            'domain': create_bed_dict(config[build]['domain']),
            'hotspot': create_bed_dict(config[build]['hotspot']),
            'curated_region': create_bed_dict(config[build]['curated_region']),
            'exon_lof_popmax': create_bed_dict(config[build]['exon_lof_popmax']),
            'pathogenic': read_pathogenic_site(config[build]['pathogenic_site']),
        }
    return _build_cache[build]
