"""Abstract base class for all data extractors."""

import logging
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from config.schema import COLUMN_NAMES, coerce_schema
from config.settings import INTERMEDIATE_DIR
from utils.checkpoint import has_checkpoint, load_checkpoint, save_checkpoint

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class: extract → transform → checkpoint pattern."""

    name: str = "base"

    def __init__(self):
        self.logger = logging.getLogger(f"extractor.{self.name}")

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Download / scrape raw data and return a DataFrame."""
        ...

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map raw columns to canonical schema. Override in subclass."""
        return df

    def run(self, resume: bool = False) -> pd.DataFrame:
        """Execute full extract → transform → save pipeline."""
        checkpoint_name = f"extractor_{self.name}"

        if resume and has_checkpoint(checkpoint_name):
            self.logger.info(f"Resuming from checkpoint: {self.name}")
            return load_checkpoint(checkpoint_name)

        self.logger.info(f"Starting extraction: {self.name}")
        raw = self.extract()
        self.logger.info(f"Extracted {len(raw):,} raw records from {self.name}")

        df = self.transform(raw)
        df = coerce_schema(df)

        # Tag every row with this source
        today = date.today().isoformat()
        df["data_sources"] = df["data_sources"].fillna("")
        mask = ~df["data_sources"].str.contains(self.name, na=False)
        df.loc[mask, "data_sources"] = df.loc[mask, "data_sources"].where(
            df.loc[mask, "data_sources"] == "", df.loc[mask, "data_sources"] + ";"
        ) + self.name
        df["data_freshness_date"] = today

        # Save intermediate parquet + checkpoint
        parquet_path = INTERMEDIATE_DIR / f"{self.name}.parquet"
        df.to_parquet(parquet_path, index=False)
        save_checkpoint(checkpoint_name, df)

        self.logger.info(
            f"Completed {self.name}: {len(df):,} records → {parquet_path}"
        )
        return df
