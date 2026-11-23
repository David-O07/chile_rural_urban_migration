"""Read CHIM files and attach municipality codes. Never writes to data/raw.

Codes are attached by POSITION, not by label: some 1992 labels name the wrong
municipality (docs/chim_interpretation.md). Every read checks that the files still have
the structure that justifies this, and stops if not.
"""

import hashlib
import re
import unicodedata
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

CHIM = Path(__file__).resolve().parents[1] / "data" / "raw" / "chim"
YEARS = (1982, 1992, 2002)
N = 304

# SHA-256 of the ordered sequences. A change means the files or their order changed,
# and the case for positional codes must be re-examined.
CODES_SHA256 = "63bf1eb927d10315b17851b3f4b161cef2791e6224ebc4232a02eb952c61ee7a"
LABELS_SHA256 = {
    1982: "bfd32c063814c10234e27d80607de87b00b867c7013672aa197bfbf53f814c71",
    1992: "381f468dd2e894e1178afadfa4df43b132d9529b23d394285a3f0b9b7677a631",
    2002: "64a58543d146942e515195328629c8e1ac4dcb9a5720bfffb43d14817fffd412",
}

# Different names for one unit, confirmed by position and population.
ALIASES = {"paiguano": "paihuano", "padrehurtado": "penaflor", "estacioncentral": "pudahuel"}


class ChimError(Exception):
    """The data does not have the structure we rely on."""


def fingerprint(values) -> str:
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def name_key(name: str) -> str:
    """Accent-free letters only. For auditing labels; never for joining."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    k = re.sub(r"[^a-z]", "", ascii_name.lower())
    return ALIASES.get(k, k)


def read_metadata(folder: Path = CHIM) -> pd.DataFrame:
    """Codes and display names, in the order that defines matrix positions."""
    book = openpyxl.load_workbook(
        folder / "documentation" / "Variable listing and metadata.xlsx", data_only=True)
    rows = [(f"{r[4]:05d}", r[5].strip())
            for r in book["CHIM Geography"].iter_rows(values_only=True) if isinstance(r[4], int)]
    meta = pd.DataFrame(rows, columns=["code", "name"])
    if len(meta) != N or not meta.code.is_unique:
        raise ChimError(f"metadata: {len(meta)} rows, expected {N} unique codes")
    if fingerprint(meta.code) != CODES_SHA256:
        raise ChimError("metadata: code sequence has changed")
    return meta


def read_raw(kind: str, year: int, folder: Path = CHIM) -> pd.DataFrame:
    """One flow or population file with its original labels, whitespace trimmed."""
    df = pd.read_csv(folder / kind / f"overall_{year}.csv", sep="\t", encoding="mac_roman")
    for c in df.columns.drop("freq"):
        df[c] = df[c].str.strip()
    return df


def check_layout(df: pd.DataFrame, n: int = N) -> list[str]:
    """Confirm a complete, regularly ordered matrix and return its label order."""
    if list(df.columns) != ["tmhabmun", "tm5ymun", "freq"]:
        raise ChimError(f"unexpected columns {list(df.columns)}")
    if len(df) != n * n:
        raise ChimError(f"{len(df)} rows, expected {n * n}")
    if df.isna().any().any() or df.freq.dtype.kind != "i" or (df.freq < 0).any():
        raise ChimError("counts must be non-missing, non-negative integers")
    labels = df.tmhabmun.iloc[:n].tolist()
    if len(set(labels)) != n:
        raise ChimError("labels repeat within one block")
    if not ((df.tmhabmun.to_numpy() == np.tile(labels, n)).all()
            and (df.tm5ymun.to_numpy() == np.repeat(labels, n)).all()):
        raise ChimError("rows are not in the expected regular order")
    return labels


def read_labels(year: int, folder: Path = CHIM) -> list[str]:
    labels = check_layout(read_raw("flows", year, folder))
    if fingerprint(labels) != LABELS_SHA256[year]:
        raise ChimError(f"{year}: label sequence has changed")
    return labels


def read_flows(year: int, folder: Path = CHIM) -> pd.DataFrame:
    """Square matrix of people. Rows: origin code (tm5ymun). Columns: destination (tmhabmun)."""
    df = read_raw("flows", year, folder)
    labels = check_layout(df)
    if fingerprint(labels) != LABELS_SHA256[year]:
        raise ChimError(f"{year}: label sequence has changed")
    codes = read_metadata(folder).code
    flows = pd.DataFrame(df.freq.to_numpy().reshape(N, N),
                         index=pd.Index(codes, name="origin"),
                         columns=pd.Index(codes, name="destination"))
    risk = read_raw("population", year, folder)
    if risk.tm5ymun.tolist() != labels or (risk.freq.to_numpy() != flows.sum(axis=1)).any():
        raise ChimError(f"{year}: population file does not equal the origin totals")
    return flows


def check_against_census(flows: pd.DataFrame, census: pd.Series, low=0.65, high=1.0) -> pd.Series:
    """Residents counted / census population. Out-of-range values suggest misplaced codes."""
    if list(census.index) != list(flows.columns):
        raise ChimError("census populations are not in matrix order")
    ratio = flows.sum(axis=0) / census
    bad = ratio[~ratio.between(low, high)]
    if len(bad):
        raise ChimError(f"implausible population ratio for {list(bad.index)}")
    return ratio


def label_audit(year: int, folder: Path = CHIM) -> pd.DataFrame:
    """Original label beside the assigned code and name, so the correction can be audited."""
    meta = read_metadata(folder)
    audit = meta.assign(position=range(1, N + 1), original_label=read_labels(year, folder))
    audit["label_agrees"] = [name_key(a) == name_key(b)
                             for a, b in zip(audit["original_label"], audit["name"])]
    return audit[["position", "original_label", "code", "name", "label_agrees"]]
