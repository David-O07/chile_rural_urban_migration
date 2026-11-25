"""Figures of aggregate results: averages by tenth of the continuum, and slopes.

    python src/figures.py

Writes reports/figures/*.png. No individual settlement is drawn.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import chim
import geography as geo
import models

FOLDER = geo.ROOT / "reports" / "figures"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLORS = ("#2a78d6", "#eb6834", "#1baf7a")
MARKERS = ("o", "s", "^")
TITLES = {"out_rate": "Out-migration", "in_rate": "In-migration"}
PERIODS = {1982: "1977-82", 1992: "1987-92", 2002: "1997-2002"}

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.edgecolor": GRID, "font.size": 10})


def style(ax, axis: str) -> None:
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def tenths() -> None:
    t = models.by_tenth(models.load("primary", "unweighted"))
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.4), sharey=True, layout="constrained")
    for ax, o in zip(axes, models.OUTCOMES):
        for y, color, marker in zip(chim.YEARS, COLORS, MARKERS):
            s = t[o].xs(y, level="year")
            ax.plot(s.index, s, color=color, marker=marker, linewidth=2, markersize=7,
                    markeredgecolor=SURFACE, label=PERIODS[y])
        ax.set_title(TITLES[o], loc="left", fontweight="bold")
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("Tenth of the continuum (1 = sparsest, 10 = largest cities)")
        style(ax, "y")
    axes[0].set_ylim(0, 40)
    axes[0].set_ylabel("Mean five-year rate (%)")
    axes[1].legend(frameon=False)
    fig.suptitle("Migration rates are highest in the sparsest places", x=0.01, ha="left")
    fig.savefig(FOLDER / "rates_by_tenth.png", dpi=180)
    plt.close(fig)


def slopes() -> None:
    d = models.run()
    d = d[d["sample"] == "unweighted"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), sharex=True, sharey=True, layout="constrained")
    series = (("primary", "Main analysis", -0.14), ("historical_boundaries", "Historical-boundary grouping", 0.14))
    for ax, o in zip(axes, models.OUTCOMES):
        for (name, label, shift), color, marker in zip(series, COLORS, MARKERS):
            r = d[(d.geography == name) & (d.outcome == o)].set_index("year").loc[list(chim.YEARS)]
            at = [i + shift for i in range(len(r))]
            ax.hlines(at, r.ci_low * 100, r.ci_high * 100, color=color, linewidth=2)
            ax.plot(r.slope * 100, at, marker, color=color, markersize=8, markeredgecolor=SURFACE, label=label)
        ax.axvline(0, color=MUTED, linewidth=1)
        ax.set_title(TITLES[o], loc="left", fontweight="bold")
        ax.set_yticks(range(len(chim.YEARS)), [PERIODS[y] for y in chim.YEARS])
        ax.set_xlabel("Slope, percentage points (95% interval)")
        style(ax, "x")
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncols=2, loc="outside lower center")
    fig.suptitle("The boundary grouping changes the slopes little", x=0.01, ha="left")
    fig.savefig(FOLDER / "slopes.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    tenths()
    slopes()


if __name__ == "__main__":
    main()
