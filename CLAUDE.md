# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

D3b-autoPVS1 is a bioinformatics tool that classifies genetic null variants (loss-of-function) according to the ACMG/AMP PVS1 criterion. It is a modified fork of the original autopvs1 by Jiguang Peng, adapted to work with pre-annotated VEP VCF files.

## Commands

### Install dependencies
```
pip install pysam pyfaidx
```

### Generate config
```
python3 config_create.py --data_dir data
```

### Run the tool
```
python3 autoPVS1_from_VEP_vcf.py --genome_version hg38 --vep_vcf /path/to/input.vcf.gz > output.tsv
```

Must be run from the repo root directory (where `config.ini` lives). Outputs TSV to stdout, logs to stderr.

### No test suite
There are currently no tests in this repository.

## Architecture

### Entry Point
- `autoPVS1_from_VEP_vcf.py` — CLI driver. Reads VEP-annotated VCF via pysam, selects best transcript per variant (`pick_transcript()`), runs PVS1 classification, outputs TSV.

### Core Modules
- `pvs1.py` — `PVS1` class implementing the full PVS1 decision flowchart. Routes to consequence-specific logic (nonsense/frameshift → NF codes, splice → SS codes, start-loss → IC codes). Classification runs eagerly at construction via `verify_PVS1` and `adjust_PVS1` properties.
- `splicing.py` — `Splicing` class for splice site strength analysis using MaxEntScan scoring. Detects cryptic splice sites, exon skipping, reading frame preservation, and NMD susceptibility.
- `strength.py` — `Strength` enum (Unset, Unmet, Supporting, Moderate, Strong, VeryStrong) with `upgrade()`/`downgrade()` methods for level adjustment.
- `utils.py` — `VCFRecord` namedtuple, BED file parsing (`create_bed_dict`, `contained_in_bed`), VEP consequence term translation, transcript lookup helpers.
- `read_data_mod.py` — Loads shared data (pvs1_levels, gene aliases, gene-transcript maps) at import time. Build-specific data (genome, transcripts, BED annotations, pathogenic sites) is lazy-loaded and cached via `get_build_data(build)` — only the requested build (hg19 or hg38) is loaded on first use.

### Vendored Libraries
- `pyhgvs/` — Python 3 port of HGVS name parser. Provides `Transcript`, `Gene`, `Exon`, `Position`, `BED6Interval` models and RefGene file parsing.
- `maxentpy/` — MaxEntScan Python wrapper for splice site scoring (5' donor and 3' acceptor matrices).

### Data Flow
```
VEP VCF → pysam → pick_transcript() → PVS1(variant, consequence, transcript)
                                         ├── verify_PVS1 → consequence-specific logic
                                         │     ├── Nonsense/Frameshift: NMD check, domain overlap, LoF frequency
                                         │     ├── Splice: MaxEntScan scoring, cryptic sites, exon skipping
                                         │     └── Start-loss: downstream ATG search, ClinVar pathogenic scoring
                                         └── adjust_PVS1 → gene-level downgrade (pvs1_levels L0-L3)
```

## Key Patterns

- **Lazy-loaded build data**: Shared data (pvs1_levels, gene maps) loads at import of `read_data_mod`. Build-specific data (genome FASTA, transcripts, BED annotations) is lazy-loaded via `get_build_data()` on first use and cached in `_build_cache`. Only the requested build is loaded, not both.
- **Genome version branching**: `PVS1` and `Splicing` constructors accept `genome_version` (hg19/hg38) and select the corresponding data globals. Methods are version-agnostic after init.
- **Criterion audit codes**: Each decision path sets `self.criterion` (e.g., NF1, SS3, IC2) providing traceability in output.
- **Special gene overrides**: Hard-coded rules exist for GJB2, PTEN, CDH1, and MYH7 in `pvs1.py`.
- **Path resolution**: `config.ini` and data file paths resolve relative to the script's directory (`os.path.dirname(__file__)`). Genome FASTA is the exception — if its path is relative, it resolves from `os.getcwd()` (for Nextflow work dir staging).
- **FASTA files not in repo**: Reference genomes must be provided separately and configured in `config.ini`. Chromosome names must have `chr` prefix.

## Output Format
Tab-separated columns: `vcf_id`, `SYMBOL`, `Feature`, `trans_name`, `consequence`, `strength_raw`, `strength`, `criterion`
