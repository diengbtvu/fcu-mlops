import logging

import pandas as pd
from zenml import step

from src.data_cleaning import EXCEL_SHEET_NAME

try:
    import openpyxl  # noqa: F401
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd  # noqa: F401
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False


class IngestData:
    """Load dataset from CSV or Excel file into a Pandas DataFrame."""

    def __init__(self, data_path: str):
        self.data_path = data_path

    def get_data(self) -> pd.DataFrame:
        logging.info(f"Ingesting data from: {self.data_path}")
        if self.data_path.endswith(('.xls', '.xlsx')):
            # Detect engine
            if self.data_path.endswith('.xls'):
                engine = 'xlrd'
            else:
                engine = 'openpyxl'
            df = pd.read_excel(
                self.data_path,
                sheet_name=EXCEL_SHEET_NAME,
                engine=engine,
            )
        else:
            df = pd.read_csv(self.data_path)
        logging.info(f"Loaded {df.shape[0]} rows × {df.shape[1]} columns.")
        return df


@step
def ingest_df(data_path: str) -> pd.DataFrame:
    """
    ZenML step: Load dataset from CSV or Excel file.

    Supports:
    - .csv  — plain CSV
    - .xls  — legacy Excel (requires xlrd)
    - .xlsx — modern Excel (requires openpyxl)
    """
    try:
        ingestor = IngestData(data_path)
        return ingestor.get_data()
    except Exception as e:
        logging.error(f"Error in ingest_df: {e}")
        raise