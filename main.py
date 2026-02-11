#!/usr/bin/env python3
"""
Veteran Organization Directory — Pipeline Orchestrator

8-stage pipeline that collects, enriches, deduplicates, and outputs
a comprehensive CSV directory of US veteran support organizations.

Usage:
    python main.py                    # Full pipeline
    python main.py --resume           # Resume from last checkpoint
    python main.py --skip-enrichment  # Skip Stage 7 (web scraping)
    python main.py --clean            # Clear all checkpoints and start fresh
    python main.py --stages 1,2,5     # Run only specific stages
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import pandas as pd

from config.settings import LOG_LEVEL, OUTPUT_DIR
from utils.checkpoint import clear_all_checkpoints

logger = logging.getLogger("pipeline")


def setup_logging(level: str = LOG_LEVEL):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(OUTPUT_DIR / "pipeline.log"),
        ],
    )


def stage1_irs_bmf(resume: bool = False):
    """Stage 1: Download and filter IRS BMF data."""
    from extractors.irs_bmf import IrsBmfExtractor

    logger.info("=" * 60)
    logger.info("STAGE 1: IRS BMF Download + Filter")
    logger.info("=" * 60)

    extractor = IrsBmfExtractor()
    return extractor.run(resume=resume)


def stage2_api_enrichment(base_df, resume: bool = False):
    """Stage 2: ProPublica + Charity Navigator API enrichment."""
    from extractors.charity_nav import CharityNavExtractor
    from extractors.propublica import PropublicaExtractor

    logger.info("=" * 60)
    logger.info("STAGE 2: API Enrichment (ProPublica + Charity Navigator)")
    logger.info("=" * 60)

    ein_list = base_df["ein"].dropna().unique().tolist()
    logger.info(f"Enriching {len(ein_list):,} unique EINs")

    # ProPublica
    pp = PropublicaExtractor(ein_list=ein_list)
    pp_df = pp.run(resume=resume)

    # Charity Navigator
    cn = CharityNavExtractor(ein_list=ein_list)
    cn_df = cn.run(resume=resume)

    return pp_df, cn_df


def stage3_web_scraping(resume: bool = False):
    """Stage 3: VA VSO + NRD web scraping."""
    from extractors.nrd import NrdExtractor
    from extractors.va_vso import VaVsoExtractor

    logger.info("=" * 60)
    logger.info("STAGE 3: Web Scraping (VA VSO + NRD)")
    logger.info("=" * 60)

    vso = VaVsoExtractor()
    vso_df = vso.run(resume=resume)

    nrd = NrdExtractor()
    nrd_df = nrd.run(resume=resume)

    return vso_df, nrd_df


def stage4_additional_sources(base_df, resume: bool = False):
    """Stage 4: VA Facilities API + NODC data."""
    from extractors.nodc import NodcExtractor
    from extractors.va_facilities import VaFacilitiesExtractor

    logger.info("=" * 60)
    logger.info("STAGE 4: Additional Sources (VA Facilities + NODC)")
    logger.info("=" * 60)

    va_fac = VaFacilitiesExtractor()
    va_fac_df = va_fac.run(resume=resume)

    ein_list = base_df["ein"].dropna().unique().tolist()
    nodc = NodcExtractor(ein_list=ein_list)
    nodc_df = nodc.run(resume=resume)

    return va_fac_df, nodc_df


def stage5_merge(base_df, pp_df, cn_df, vso_df, nrd_df, va_fac_df, nodc_df):
    """Stage 5: Merge all sources."""
    from loaders.merger import merge_all

    logger.info("=" * 60)
    logger.info("STAGE 5: Merge All Sources")
    logger.info("=" * 60)

    ein_sources = {
        "propublica": pp_df,
        "charity_nav": cn_df,
        "nodc": nodc_df,
    }

    non_ein_sources = {
        "va_vso": vso_df,
        "nrd": nrd_df,
        "va_facilities": va_fac_df,
    }

    merged = merge_all(base_df, ein_sources, non_ein_sources)
    logger.info(f"Merged result: {len(merged):,} records")
    return merged


def stage6_dedup(df):
    """Stage 6: Three-tier deduplication."""
    from loaders.deduplicator import deduplicate

    logger.info("=" * 60)
    logger.info("STAGE 6: Deduplication")
    logger.info("=" * 60)

    deduped = deduplicate(df)
    logger.info(f"After dedup: {len(deduped):,} records (removed {len(df) - len(deduped):,})")
    return deduped


def filter_by_state(df: pd.DataFrame, state_code: str) -> pd.DataFrame:
    """Filter DataFrame to orgs in a specific state before enrichment."""
    logger.info("=" * 60)
    logger.info(f"STATE FILTER: Filtering to {state_code}")
    logger.info("=" * 60)

    # Case-insensitive state matching (IRS BMF uses uppercase, other sources may vary)
    mask = df["state"].str.upper() == state_code.upper()
    filtered = df[mask].copy()

    logger.info(f"State filter: {len(filtered):,} of {len(df):,} orgs "
                 f"({len(filtered)/max(len(df),1)*100:.1f}%)")

    if len(filtered) == 0:
        logger.warning(f"No orgs found for state '{state_code}'. "
                       "Check that the state column contains 2-letter codes.")

    return filtered


def stage7_enrichment(df):
    """Stage 7: Web enrichment for social media and email."""
    from transformers.enricher import WebEnricher

    logger.info("=" * 60)
    logger.info("STAGE 7: Web Enrichment (social media / email)")
    logger.info("=" * 60)

    enricher = WebEnricher()
    enriched = enricher.enrich(df)
    return enriched


def stage8_output(df):
    """Stage 8: Normalize, calculate confidence, write CSV + report."""
    from loaders.csv_writer import write_csv
    from transformers.normalizer import normalize_dataframe

    logger.info("=" * 60)
    logger.info("STAGE 8: Normalize + CSV Output")
    logger.info("=" * 60)

    df = normalize_dataframe(df)
    csv_path = write_csv(df)
    logger.info(f"Final CSV: {csv_path}")
    return csv_path


def main():
    parser = argparse.ArgumentParser(
        description="Veteran Organization Directory Pipeline"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Clear all checkpoints and start fresh"
    )
    parser.add_argument(
        "--skip-enrichment", action="store_true",
        help="Skip Stage 7 (web scraping for social media)"
    )
    parser.add_argument(
        "--stages", type=str, default=None,
        help="Comma-separated list of stages to run (e.g., '1,2,5')"
    )
    parser.add_argument(
        "--state-filter", type=str, default=None,
        help="Filter to specific state before enrichment (e.g., 'KY' for Kentucky)"
    )
    args = parser.parse_args()

    setup_logging()

    if args.clean:
        logger.info("Cleaning all checkpoints...")
        clear_all_checkpoints()

    start_time = time.time()
    logger.info("=" * 60)
    logger.info("VETERAN ORGANIZATION DIRECTORY PIPELINE")
    logger.info(f"Started: {datetime.now().isoformat(timespec='seconds')}")
    logger.info(f"Resume: {args.resume} | Skip enrichment: {args.skip_enrichment}")
    logger.info("=" * 60)

    # Determine which stages to run
    if args.stages:
        run_stages = {int(s.strip()) for s in args.stages.split(",")}
    else:
        run_stages = {1, 2, 3, 4, 5, 6, 7, 8}

    if args.skip_enrichment:
        run_stages.discard(7)

    # Initialize DataFrames
    import pandas as pd
    base_df = pd.DataFrame()
    pp_df = pd.DataFrame()
    cn_df = pd.DataFrame()
    vso_df = pd.DataFrame()
    nrd_df = pd.DataFrame()
    va_fac_df = pd.DataFrame()
    nodc_df = pd.DataFrame()

    try:
        # Stage 1: IRS BMF
        if 1 in run_stages:
            base_df = stage1_irs_bmf(resume=args.resume)
        else:
            # Try to load from checkpoint
            from utils.checkpoint import load_checkpoint
            base_df = load_checkpoint("extractor_irs_bmf")
            if base_df is None:
                logger.error("Stage 1 skipped but no checkpoint found. Run stage 1 first.")
                sys.exit(1)

        # Stage 2: API enrichment
        if 2 in run_stages:
            pp_df, cn_df = stage2_api_enrichment(base_df, resume=args.resume)
        else:
            from utils.checkpoint import load_checkpoint
            _pp = load_checkpoint("extractor_propublica")
            pp_df = _pp if _pp is not None else pd.DataFrame()
            _cn = load_checkpoint("extractor_charity_nav")
            cn_df = _cn if _cn is not None else pd.DataFrame()

        # Stage 3: Web scraping
        if 3 in run_stages:
            vso_df, nrd_df = stage3_web_scraping(resume=args.resume)
        else:
            from utils.checkpoint import load_checkpoint
            _vso = load_checkpoint("extractor_va_vso")
            vso_df = _vso if _vso is not None else pd.DataFrame()
            _nrd = load_checkpoint("extractor_nrd")
            nrd_df = _nrd if _nrd is not None else pd.DataFrame()

        # Stage 4: Additional sources
        if 4 in run_stages:
            va_fac_df, nodc_df = stage4_additional_sources(base_df, resume=args.resume)
        else:
            from utils.checkpoint import load_checkpoint
            _vaf = load_checkpoint("extractor_va_facilities")
            va_fac_df = _vaf if _vaf is not None else pd.DataFrame()
            _nodc = load_checkpoint("extractor_nodc")
            nodc_df = _nodc if _nodc is not None else pd.DataFrame()

        # Stage 5: Merge
        if 5 in run_stages:
            merged = stage5_merge(base_df, pp_df, cn_df, vso_df, nrd_df, va_fac_df, nodc_df)
        else:
            merged = base_df  # fallthrough

        # Stage 6: Dedup
        if 6 in run_stages:
            merged = stage6_dedup(merged)

        # Stage 7: Web enrichment (optional)
        if 7 in run_stages:
            if args.state_filter:
                enrichment_df = filter_by_state(merged, args.state_filter)
                enrichment_df = stage7_enrichment(enrichment_df)
                # Merge enrichments back into full dataset
                merged.update(enrichment_df)
            else:
                merged = stage7_enrichment(merged)

        # Stage 8: Output
        if 8 in run_stages:
            csv_path = stage8_output(merged)

        elapsed = time.time() - start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        logger.info("=" * 60)
        logger.info(f"PIPELINE COMPLETE in {hours}h {minutes}m {seconds}s")
        logger.info(f"Final record count: {len(merged):,}")
        if 8 in run_stages:
            logger.info(f"Output: {csv_path}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user. Progress has been checkpointed.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
