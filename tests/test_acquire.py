"""Failure cases for acquire.py, using tiny synthetic archives (no real data)."""

import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import acquire as aq


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "server.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("a.txt", "hello " * 5000)
    data = path.read_bytes()
    ds = aq.Dataset("toy", path.as_uri(), "toy.zip", len(data), hashlib.sha256(data).hexdigest())
    return ds, data


def test_download_is_complete_and_leaves_no_part(source, tmp_path):
    ds, data = source
    final = aq.acquire(ds, tmp_path / "raw")
    assert final.read_bytes() == data
    assert not aq.part_path(final).exists()


def test_resumes_partial_download(source, tmp_path, capsys):
    ds, data = source
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "toy.zip.part").write_bytes(data[:1000])
    assert aq.acquire(ds, raw).read_bytes() == data
    assert "resuming at 1,000" in capsys.readouterr().out


def test_corrupt_partial_is_never_promoted(source, tmp_path):
    ds, data = source
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "toy.zip.part").write_bytes(b"X" * 1000)
    with pytest.raises(aq.AcquisitionError, match="checksum"):
        aq.acquire(ds, raw)
    assert not (raw / "toy.zip").exists()


def test_failed_download_keeps_partial(source, tmp_path):
    ds, data = source
    missing = aq.Dataset("toy", "file:///no/such/file", "toy.zip", ds.size, ds.sha256)
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "toy.zip.part").write_bytes(data[:1000])
    with pytest.raises(aq.AcquisitionError, match="curl"):
        aq.acquire(missing, raw)
    assert (raw / "toy.zip.part").read_bytes() == data[:1000]


def test_existing_wrong_file_is_not_touched(source, tmp_path):
    ds, data = source
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "toy.zip").write_bytes(b"mine")
    with pytest.raises(aq.AcquisitionError):
        aq.acquire(ds, raw)
    assert (raw / "toy.zip").read_bytes() == b"mine"


def test_html_error_page_is_rejected(tmp_path):
    page = tmp_path / "page"
    page.write_bytes(b"<html>blocked</html>")
    ds = aq.Dataset("toy", page.as_uri(), "toy.zip", page.stat().st_size, None)
    with pytest.raises(aq.AcquisitionError, match="not a zip"):
        aq.acquire(ds, tmp_path / "raw")


def test_from_file_is_verified_too(source, tmp_path):
    ds, data = source
    wrong = tmp_path / "wrong.zip"
    wrong.write_bytes(data[:-1] + b"?")
    with pytest.raises(aq.AcquisitionError, match="checksum"):
        aq.acquire(ds, tmp_path / "raw", wrong)


def test_extract_reruns_but_rejects_edited_file(source, tmp_path):
    ds, _ = source
    target = tmp_path / "out" / "a.txt"
    with zipfile.ZipFile(aq.acquire(ds, tmp_path / "raw")) as z:
        aq.extract(z, "a.txt", target)
        aq.extract(z, "a.txt", target)
        target.chmod(0o644)
        target.write_text("HELLO " * 5000)  # same length, different content
        with pytest.raises(aq.AcquisitionError, match="differs"):
            aq.extract(z, "a.txt", target)


def test_chim_extraction_takes_only_what_is_needed(tmp_path):
    def zipped(files):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for name, text in files.items():
                z.writestr(name, text)
        return buffer.getvalue()

    matrices = {f"Matrices/{y}/overall/overall_{y}.csv": f"m{y}" for y in aq.YEARS}
    matrices["Matrices/1982/sex and age/data_1_2_1982.csv"] = "not wanted"
    population = {f"Population/{y}/overall/overall_{y}.csv": f"p{y}" for y in aq.YEARS}
    archive = tmp_path / "CHIM.zip"
    archive.write_bytes(zipped({
        "Documentation/readme.rtf": "r", "Documentation/.DS_Store": "x",
        "Matrices.zip": zipped(matrices), "Population.zip": zipped(population),
        "GIS files.zip": zipped({"GIS files/Harmonised Municipalities/h.shp": "s"}),
    }))
    out = tmp_path / "out"
    aq.extract_chim(archive, out)
    found = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}
    assert found == {"documentation/readme.rtf", "gis/h.shp"} | {
        f"{kind}/overall_{y}.csv" for kind in ("flows", "population") for y in aq.YEARS}
