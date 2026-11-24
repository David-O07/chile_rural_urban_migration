"""Local report: historical-boundary scenario and sample sizes. No regressions.

    python src/report_sensitivity.py
"""

import pandas as pd

import chim
import geography as geo
import measures as ms
import samples as sp

REPORT = geo.ROOT / "reports" / "local" / "sensitivity_report.md"


def main() -> None:
    ev = geo.load_evidence()
    raw = {y: chim.read_flows(y) for y in chim.YEARS}
    by = {s.name: s for s in geo.SCENARIOS}
    built = {n: geo.build(ev, by[n], raw) for n in ("primary", "historical_boundaries")}
    d = {n: ms.measure(g.settlements, g.flows) for n, g in built.items()}
    name = dict(zip(ev.meta.code, ev.meta["name"]))
    out = ["# Sensitivity report (local only)\n", "## Flows of the eight pairs (forward / reverse)\n"]
    out.append(pd.DataFrame([{"pair": f"{name[o]} -> {name[t]}",
                              **{f"{y}": f"{raw[y].loc[o, t]} / {raw[y].loc[t, o]}" for y in raw}}
                             for o, t in geo.DL2868_PAIRS]).to_string(index=False))
    out.append("\n## Groups\n")
    g = built["historical_boundaries"].settlements
    out.append(g[g.settlement_id.str.startswith("H")][["settlement_id", "settlement_name", "type", "area_km2", "n_neighbours"]].to_string(index=False))
    out.append("\n## Members before, and groups after\n")
    codes = {c for p in geo.DL2868_PAIRS for c in p}
    cols = ["year", "settlement_name", "origin_pop", "destination_pop", "departures", "arrivals", "out_rate", "in_rate", "position"]
    a = d["primary"]
    out.append(a[a.settlement_id.isin({f"R{c}" for c in codes})][cols].round(3).to_string(index=False))
    b = d["historical_boundaries"]
    out.append(b[b.settlement_id.str.startswith("H")][cols].round(3).to_string(index=False))
    for n, t in d.items():
        out += [f"\n## Distributions: {n}\n", ms.distribution(t).to_string(index=False)]
    out += ["\n## National\n"]
    for n, g in built.items():
        for y, acc in g.accounts.items():
            out.append(f"{n} {y}: movers {acc['movers_settlement']:,} of {acc['people_after']:,} = {acc['movers_settlement'] / acc['people_after']:.4%}")
    size = pd.concat([sp.sizes(t, n) for n, t in d.items()])
    out += ["\n## Sample sizes\n", size.to_string(index=False)]
    REPORT.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
