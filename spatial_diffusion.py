"""Run the analysis from raw data to tables and figures.

    python src/acquire.py            # once, downloads the raw data
    python spatial_diffusion.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import figures
import measures
import models


def main() -> None:
    measures.main()   # geography, flows, positions and rates
    models.main()     # regressions and tables
    figures.main()


if __name__ == "__main__":
    main()
