"""Download, verify and selectively extract the raw datasets. No cleaning happens here.

    python src/acquire.py                                  # everything
    python src/acquire.py --from-file chim ~/Downloads/CHIM.zip   # browser download

Safe to rerun: complete files are re-verified, partial downloads resume, and an
existing file is never overwritten.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
YEARS = (1982, 1992, 2002)
JRC = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"


class AcquisitionError(Exception):
    """A file is missing, incomplete or not what we expected."""


# --- 1. Catalogue -------------------------------------------------------------

@dataclass(frozen=True)
class Dataset:
    name: str
    url: str
    filename: str
    size: int
    sha256: str | None  # None: skip the comparison (first download)


DATASETS = [
    Dataset(
        "chim",
        "https://uchicago.app.box.com/index.php?rm=box_download_shared_file"
        "&shared_name=yqc97nq23hoeeqo5lkc2grlg98skokgk&file_id=f_684554934210",
        "CHIM.zip",
        731_174_792,
        "cf315e541993aef04b56dd77e5da470f0363ea3cbd543403cec277c8f01eeb8b",
    ),
    Dataset(
        "ghs_fua",
        f"{JRC}/GHS_FUA_UCDB2015_GLOBE_R2019A/V1-0/"
        "GHS_FUA_UCDB2015_GLOBE_R2019A_54009_1K_V1_0.zip",
        "GHS_FUA_UCDB2015_GLOBE_R2019A_54009_1K_V1_0.zip",
        3_059_037,
        "d54de59b82b8c4d64a710f90ccd554975a3be92233f14115ac154094c3549979",
    ),
    Dataset(
        "ghs_pop",
        f"{JRC}/GHS_POP_MT_GLOBE_R2019A/GHS_POP_E2015_GLOBE_R2019A_54009_1K/V1-0/"
        "GHS_POP_E2015_GLOBE_R2019A_54009_1K_V1_0.zip",
        "GHS_POP_E2015_GLOBE_R2019A_54009_1K_V1_0.zip",
        137_934_966,
        "8cda2bfd1dbdc7b2bc0fd9a08afa92efc202d37092d09e7bf1779c42fbe29559",
    ),
]


# --- 2-5. Download, verify, promote -------------------------------------------

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, ds: Dataset) -> str:
    """Check size, checksum and zip integrity, cheapest first. Return the checksum."""
    size = path.stat().st_size
    if size != ds.size:
        raise AcquisitionError(f"{path}: {size:,} bytes, expected {ds.size:,}")
    digest = sha256(path)
    if ds.sha256 and digest != ds.sha256:
        raise AcquisitionError(f"{path}: checksum {digest}, expected {ds.sha256}")
    if not zipfile.is_zipfile(path):
        raise AcquisitionError(f"{path}: not a zip file")
    with zipfile.ZipFile(path) as z:
        try:
            bad = z.testzip()
        except zipfile.BadZipFile as e:
            raise AcquisitionError(f"{path}: {e}") from e
        if bad:
            raise AcquisitionError(f"{path}: corrupted member {bad}")
    return digest


def part_path(path: Path) -> Path:
    return path.with_name(path.name + ".part")


def promote(part: Path, final: Path) -> None:
    """Give a finished file its final name. Both names are on the same disk."""
    if final.exists():
        raise AcquisitionError(f"{final} already exists; not overwriting")
    part.rename(final)
    final.chmod(0o444)  # read-only: guards against accidental edits


def fetch(url: str, part: Path, size: int) -> None:
    """Download to the .part file, continuing from any bytes already there."""
    have = part.stat().st_size if part.exists() else 0
    if have > size:
        raise AcquisitionError(f"{part} is larger than expected; inspect or delete it")
    if have == size:
        return
    if have:
        print(f"  resuming at {have:,} of {size:,} bytes")
    result = subprocess.run([
        "curl", "--fail", "--location", "--silent", "--show-error",
        "--continue-at", "-", "--retry", "3", "--connect-timeout", "30",
        "--speed-limit", "1000", "--speed-time", "60",  # give up if stalled
        "--output", str(part), url,
    ])
    if result.returncode != 0:
        raise AcquisitionError(
            f"curl exited with {result.returncode}. Any partial file is kept; rerun to resume."
        )


def acquire(ds: Dataset, folder: Path, local_copy: Path | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / ds.filename
    part = part_path(final)
    if final.exists():
        digest = verify(final, ds)
        print(f"  already present and verified  sha256={digest}")
        return final
    if local_copy:
        if part.exists():
            raise AcquisitionError(f"{part} exists; delete it before using --from-file")
        shutil.copyfile(local_copy, part)
    else:
        fetch(ds.url, part, ds.size)
    digest = verify(part, ds)
    promote(part, final)
    print(f"  verified  {ds.size:,} bytes  sha256={digest}")
    return final


# --- 6. Selective extraction --------------------------------------------------

def extract(archive: zipfile.ZipFile, member: str, target: Path) -> None:
    """Copy one member out of an archive. zipfile checks its CRC while reading."""
    info = archive.getinfo(member)
    if target.exists():
        if target.stat().st_size != info.file_size:
            raise AcquisitionError(f"{target} differs from the archive")
        with archive.open(info) as a, target.open("rb") as b:
            while chunk := a.read(1 << 20):
                if chunk != b.read(len(chunk)):
                    raise AcquisitionError(f"{target} differs from the archive")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    part = part_path(target)
    with archive.open(info) as src, part.open("wb") as dst:  # restarts if interrupted
        shutil.copyfileobj(src, dst)
    promote(part, target)


def wanted(archive: zipfile.ZipFile, prefix: str) -> list[str]:
    """Real files under a folder, ignoring macOS clutter."""
    return [
        n for n in archive.namelist()
        if n.startswith(prefix) and not n.endswith("/")
        and "__MACOSX" not in n and ".DS_Store" not in n
    ]


def extract_chim(archive_path: Path, folder: Path) -> None:
    """Read the nested zips in place, so Matrices.zip (8.4 GB expanded) is never unpacked."""
    with zipfile.ZipFile(archive_path) as outer:
        for name in wanted(outer, "Documentation/"):
            extract(outer, name, folder / "documentation" / Path(name).name)
        for inner_zip, top, out in [("Matrices.zip", "Matrices", "flows"),
                                    ("Population.zip", "Population", "population")]:
            with outer.open(inner_zip) as f, zipfile.ZipFile(f) as inner:
                for y in YEARS:
                    extract(inner, f"{top}/{y}/overall/overall_{y}.csv",
                            folder / out / f"overall_{y}.csv")
        with outer.open("GIS files.zip") as f, zipfile.ZipFile(f) as inner:
            for name in wanted(inner, "GIS files/Harmonised Municipalities/"):
                extract(inner, name, folder / "gis" / Path(name).name)


def extract_all(archive_path: Path, folder: Path) -> None:
    with zipfile.ZipFile(archive_path) as z:
        for name in wanted(z, ""):
            extract(z, name, folder / Path(name).name)


# --- 7. Read-only content checks ----------------------------------------------

def check_contents(raw: Path) -> None:
    import pyogrio
    import rasterio

    for y in YEARS:
        for kind, rows, columns in [("flows", 304 * 304, 3), ("population", 304, 2)]:
            path = raw / "chim" / kind / f"overall_{y}.csv"
            with path.open(encoding="latin-1") as f:
                header = f.readline().rstrip("\r\n").split("\t")
                n = sum(1 for line in f if line.strip())
            if n != rows or len(header) != columns:
                raise AcquisitionError(f"{path}: {n} rows, {len(header)} columns")
            print(f"  {kind} {y}: {n:,} rows, columns {header}")

    shp, = (raw / "chim" / "gis").glob("*.shp")
    info = pyogrio.read_info(shp)
    print(f"  boundaries: {info['features']} {info['geometry_type']}, fields {list(info['fields'])}")
    if info["features"] != 304:
        raise AcquisitionError("expected 304 boundaries")

    gpkg, = (raw / "ghs_fua").glob("*.gpkg")
    info = pyogrio.read_info(gpkg)
    chile = pyogrio.read_dataframe(gpkg, where="Cntry_ISO = 'CHL'", read_geometry=False)
    print(f"  FUAs: {info['features']:,} worldwide, {len(chile)} Chile, crs {info['crs']}")
    if len(chile) != 31:
        raise AcquisitionError("expected 31 Chilean FUAs")

    tif, = (raw / "ghs_pop").glob("*.tif")
    with rasterio.open(tif) as r:
        print(f"  population grid: {r.width:,} x {r.height:,}, {r.count} band, {r.dtypes[0]}, "
              f"cell {r.res}, nodata {r.nodata}, bounds {tuple(r.bounds)}")
        print(f"  population grid crs: {r.crs.to_string()}")
        if r.res != (1000.0, 1000.0) or r.count != 1:
            raise AcquisitionError("expected one band of 1 km cells")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", nargs=2, metavar=("DATASET", "PATH"),
                        help="use a file downloaded by hand")
    args = parser.parse_args()
    local = {}
    if args.from_file:
        name, path = args.from_file
        if name not in {d.name for d in DATASETS}:
            parser.error(f"unknown dataset {name}")
        local[name] = Path(path).expanduser()
    try:
        for ds in DATASETS:
            print(f"{ds.name}:")
            folder = RAW / ds.name
            archive = acquire(ds, folder, local.get(ds.name))
            (extract_chim if ds.name == "chim" else extract_all)(archive, folder)
        print("contents:")
        check_contents(RAW)
    except (AcquisitionError, OSError, KeyError, zipfile.BadZipFile) as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
