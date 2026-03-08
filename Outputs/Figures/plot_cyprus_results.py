"""
plot_cyprus_results.py
======================
Academic-quality figures for the Cyprus 2030 capacity-expansion study.
Reads sensitivity_results.csv and base_dispatch.csv directly.

Usage
-----
    python model/plot_cyprus_results.py

Outputs (in ./model/outputs/figures/)
-------------------------------------
    fig01_cost_decomposition_base.pdf
    fig01b_investment_decomposition_base.pdf
    fig02_generation_mix_base.pdf
    fig03_cost_vs_carbon.pdf
    fig04_cost_vs_oil.pdf
    fig05_investment_vs_carbon.pdf
    fig06_battery_vs_carbon.pdf
    fig07_carbon_cost_component.pdf
    fig08_fuel_mix_vs_carbon.pdf
    fig09_curtailment_vs_carbon.pdf
    fig10_nse_vs_carbon.pdf
    fig11_oil_generation_vs_factor.pdf
    fig12_investment_cost_vs_oil.pdf
    fig13_oil_phase_down_table.pdf
    fig14_dispatch_profile_week.pdf
    fig15_duration_curve.pdf
    fig16_cost_emissions_pareto.pdf
    fig21_capacity_before_after_base.pdf
    fig22_capacity_composition_base.pdf
    fig23_battery_capacity_before_after_base.pdf
    fig24_total_capacity_vs_carbon.pdf
    fig25_total_capacity_vs_oil.pdf
    fig26_base_capacity_factor.pdf
    fig27_oil0_cost_reliability_vs_carbon.pdf
    fig28_oil0_worth_it_tradeoff.pdf
    fig29_oil0_abatement_cost_vs_carbon.pdf
    fig30_lowoil_cost_reliability_vs_carbon.pdf
    fig31_lowoil_worth_it_vs_oil10.pdf
    fig32_base_curtailment_monthly.pdf
    fig33_cost_heatmap_voll_oil_carbon.pdf
    fig34_build_decision_ranges_boxplot.pdf
    table34_build_decision_ranges.csv

Requirements: numpy, pandas, matplotlib
    pip install numpy pandas matplotlib
"""

import os
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# 0.  PATHS
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = SCRIPT_DIR / "outputs"
SENS_CSV = OUTPUTS_DIR / "sensitivity_results.csv"
DISPATCH_CSV = OUTPUTS_DIR / "base_dispatch.csv"
OUT_DIR = OUTPUTS_DIR / "figures"

# This plotting script is anchored to model/outputs so it stays portable.
os.makedirs(OUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  STYLE  — clean academic look (no seaborn dependency)
# ─────────────────────────────────────────────────────────────────────────────
PAPER   = "#f5f2eb"
INK     = "#0d0d0d"
MUTED   = "#7a7060"
RULE    = "#c8c0aa"
RED     = "#c84b2f"
BLUE    = "#2f6bc8"
GREEN   = "#2a8a4a"
GOLD    = "#c8a020"
PURPLE  = "#7b3fa0"
TEAL    = "#1a8080"

PALETTE_OIL    = [RED, "#e07030", GOLD, GREEN, BLUE, PURPLE, TEAL]
PALETTE_CARBON = [INK, "#3a5080", BLUE, GREEN, GOLD, RED]

mpl.rcParams.update({
    # fonts
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size":            9,
    "axes.titlesize":       10,
    "axes.labelsize":       9,
    "xtick.labelsize":      8,
    "ytick.labelsize":      8,
    "legend.fontsize":      8,
    "figure.titlesize":     11,
    # layout
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.linewidth":       0.7,
    "axes.edgecolor":       INK,
    "axes.facecolor":       "white",
    "figure.facecolor":     "white",
    "axes.grid":            True,
    "grid.color":           RULE,
    "grid.linewidth":       0.45,
    "grid.linestyle":       "-",
    "axes.axisbelow":       True,
    # ticks
    "xtick.direction":      "out",
    "ytick.direction":      "out",
    "xtick.major.size":     3.5,
    "ytick.major.size":     3.5,
    "xtick.major.width":    0.7,
    "ytick.major.width":    0.7,
    "xtick.color":          INK,
    "ytick.color":          INK,
    # lines
    "lines.linewidth":      1.6,
    "lines.markersize":     5,
    "patch.linewidth":      0.5,
    # legend
    "legend.frameon":       True,
    "legend.framealpha":    0.92,
    "legend.edgecolor":     RULE,
    "legend.fancybox":      False,
    # saving
    "savefig.dpi":          300,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.05,
    "pdf.fonttype":         42,   # embeds fonts in PDF
})

def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.savefig(path, bbox_inches="tight")
    plt.savefig(path.replace(".pdf", ".png"), bbox_inches="tight", dpi=200)
    plt.close()
    print(f"  ✓  {name}")

def label_bar(ax, rects, fmt="{:.0f}", pad=2, **kw):
    """Annotate bar tops."""
    for r in rects:
        h = r.get_height()
        if h > 0:
            ax.text(r.get_x() + r.get_width() / 2, h + pad,
                    fmt.format(h), ha="center", va="bottom",
                    fontsize=7, color=INK, **kw)


def find_first_col(df, candidates):
    """Return first matching column name from candidates, else None."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def allocate_by_proxy(total_value, proxy_series):
    """Allocate annual total across months proportional to a non-negative proxy."""
    proxy = proxy_series.astype(float).clip(lower=0)
    denom = proxy.sum()
    if denom <= 0:
        return pd.Series(0.0, index=proxy.index, dtype=float)
    return total_value * proxy / denom

# ─────────────────────────────────────────────────────────────────────────────
# 2.  LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
print("Loading data …")
sens = pd.read_csv(SENS_CSV)
disp = pd.read_csv(DISPATCH_CSV, parse_dates=["timestamp"])

# Required hourly dispatch columns used in the paper figures.
required_dispatch_cols = [
    "timestamp", "p_pv", "p_wind", "p_oil", "p_gas",
    "demand_mwh", "charge_total", "discharge_total", "curt_pv", "curt_wind",
]
missing_dispatch_cols = [c for c in required_dispatch_cols if c not in disp.columns]
if missing_dispatch_cols:
    raise ValueError(
        "base_dispatch.csv is missing required columns for the plotting pack.\n"
        f"Missing: {missing_dispatch_cols}\n"
        f"Required: {required_dispatch_cols}"
    )

# Convenience derived columns
sens["total_cost_M"]      = sens["objective_value"]  / 1e6
sens["invest_M"]          = sens["investment_cost"]  / 1e6
sens["opex_M"]            = sens["operating_cost"]   / 1e6
sens["oil_cost_M"]        = sens["oil_cost_total"]   / 1e6
sens["gas_cost_M"]        = sens["gas_cost_total"]   / 1e6
sens["carbon_cost_M"]     = sens["carbon_cost_component"] / 1e6
sens["curt_pen_M"]        = sens["curtailment_penalty_component"] / 1e6
sens["voll_cost_M"]       = sens["voll_cost_component"] / 1e6
sens["dcap_pv_MW"]        = sens["dcap_pv"]
sens["dcap_wind_MW"]      = sens["dcap_wind"]
sens["dcap_gas_MW"]       = sens["dcap_gas"]
sens["bat_total_MWh"]     = sens["Ebat_total"]
sens["oil_factor_pct"]    = (sens["oil_factor"] * 100).round(1)
sens["gen_pv_TWh"]        = sens["total_generation_pv"]   / 1e6
sens["gen_wind_TWh"]      = sens["total_generation_wind"] / 1e6
sens["gen_oil_TWh"]       = sens["total_generation_oil"]  / 1e6
sens["gen_gas_TWh"]       = sens["total_generation_gas"]  / 1e6
sens["implied_co2_Mt"]    = (sens["total_generation_oil"] * 0.708 +
                             sens["total_generation_gas"] * 0.381) / 1e6

# Capacity interpretation:
# In this dataset, cap_* columns are treated as "after optimisation" capacities
# when they match cap_exist_* + dcap_* (checked for PV/Wind/Gas). Otherwise, we
# explicitly construct after-capacity from existing + new build.
cap_cols_available = all(c in sens.columns for c in [
    "cap_pv", "cap_wind", "cap_oil", "cap_gas",
    "cap_exist_pv", "cap_exist_wind", "cap_exist_oil", "cap_exist_gas",
    "dcap_pv", "dcap_wind", "dcap_gas",
])
use_cap_as_after = False
if cap_cols_available:
    use_cap_as_after = (
        np.allclose(sens["cap_pv"], sens["cap_exist_pv"] + sens["dcap_pv"], atol=1e-6)
        and np.allclose(sens["cap_wind"], sens["cap_exist_wind"] + sens["dcap_wind"], atol=1e-6)
        and np.allclose(sens["cap_gas"], sens["cap_exist_gas"] + sens["dcap_gas"], atol=1e-6)
    )

if use_cap_as_after:
    sens["cap_after_pv"] = sens["cap_pv"]
    sens["cap_after_wind"] = sens["cap_wind"]
    sens["cap_after_oil"] = sens["cap_oil"]
    sens["cap_after_gas"] = sens["cap_gas"]
else:
    sens["cap_after_pv"] = sens["cap_exist_pv"] + sens["dcap_pv"]
    sens["cap_after_wind"] = sens["cap_exist_wind"] + sens["dcap_wind"]
    sens["cap_after_gas"] = sens["cap_exist_gas"] + sens["dcap_gas"]
    # Oil new-build is not a decision in this simplified model; keep existing oil.
    sens["cap_after_oil"] = sens["cap_exist_oil"]

sens["newbuild_pv_MW"] = (sens["cap_after_pv"] - sens["cap_exist_pv"]).clip(lower=0)
sens["newbuild_wind_MW"] = (sens["cap_after_wind"] - sens["cap_exist_wind"]).clip(lower=0)
sens["newbuild_oil_MW"] = (sens["cap_after_oil"] - sens["cap_exist_oil"]).clip(lower=0)
sens["newbuild_gas_MW"] = (sens["cap_after_gas"] - sens["cap_exist_gas"]).clip(lower=0)

# For "before" capacity plots, oil should show full installed baseline (100%),
# not the scenario-limited effective availability.
if "cap_exist_oil_base" in sens.columns:
    sens["cap_exist_oil_full"] = pd.to_numeric(sens["cap_exist_oil_base"], errors="coerce")
else:
    sens["cap_exist_oil_full"] = pd.to_numeric(sens["cap_exist_oil"], errors="coerce")
    valid_oil = sens["oil_factor"] > 1e-9
    sens.loc[valid_oil, "cap_exist_oil_full"] = (
        pd.to_numeric(sens.loc[valid_oil, "cap_exist_oil"], errors="coerce")
        / pd.to_numeric(sens.loc[valid_oil, "oil_factor"], errors="coerce")
    )

# Base case row  (oil=30%, VoLL=6500, CO2=€30)
base_mask = (sens["oil_factor"] == 0.30) & (sens["voll"] == 6500.0) & (sens["carbon_tax"] == 30.0)
base = sens[base_mask].iloc[0]

# Subsets by axes
CO2_LEVELS  = sorted(sens["carbon_tax"].unique())
OIL_FACTORS = sorted(sens["oil_factor"].unique())
VOLL_LEVELS = sorted(sens["voll"].unique())
VOLL_BASE   = 6500.0

def q(df, oil=None, voll=None, co2=None):
    """Quick query helper."""
    mask = pd.Series(True, index=df.index)
    if oil  is not None: mask &= df["oil_factor"] == oil
    if voll is not None: mask &= df["voll"]        == voll
    if co2  is not None: mask &= df["carbon_tax"]  == co2
    return df[mask].sort_values(["oil_factor", "carbon_tax", "voll"])

print(f"  Sensitivity: {len(sens)} rows | CO₂ levels: {CO2_LEVELS} | Oil factors: {OIL_FACTORS}")
print(f"  Dispatch: {len(disp)} rows | columns: {list(disp.columns[:8])} …")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 01 — Base Case Cost Decomposition (stacked bar)
# ─────────────────────────────────────────────────────────────────────────────
print("\nGenerating figures …")

fig, ax = plt.subplots(figsize=(5.5, 3.8))

components = {
    "Investment (CAPEX + FOM)": base["invest_M"],
    "Gas fuel":                 base["gas_cost_M"] - base["carbon_cost_M"],
    "Carbon tax":               base["carbon_cost_M"],
    "Oil fuel":                 base["oil_cost_M"],
    "Curtailment penalty":      base["curt_pen_M"],
    "VoLL (unserved energy)":   base["voll_cost_M"],
}
colors = [INK, RED, GOLD, MUTED, BLUE, "#a03030"]
labels = list(components.keys())
values = list(components.values())

bottom, bars = 0, []
for val, col, lab in zip(values, colors, labels):
    b = ax.bar(0.5, val, bottom=bottom, color=col, width=0.45, label=lab, zorder=3)
    if val > 3:
        ax.text(0.5, bottom + val / 2, f"€{val:.1f}M", ha="center", va="center",
                fontsize=7.5, color="white" if col in [INK, RED, MUTED] else INK,
                fontweight="bold")
    bottom += val
    bars.append(b)

ax.set_xlim(0, 1)
ax.set_xticks([])
ax.set_ylabel("Annual Cost (M€/year)")
ax.set_title("Base Case Cost Decomposition\n"
             r"Oil 30% · VoLL €6,500/MWh · CO$_2$ €30/tCO$_2$",
             pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0)
ax.text(0.5, bottom + 5, f"Total: €{bottom:.1f}M", ha="center",
        fontsize=8.5, fontweight="bold", color=INK)
ax.set_ylim(0, bottom * 1.12)
ax.grid(axis="x", visible=False)
savefig("fig01_cost_decomposition_base.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 01b — Base Case Investment Decomposition by Technology (stacked bar)
# ─────────────────────────────────────────────────────────────────────────────
# Infer annualized unit investment coefficients from the sensitivity table:
# investment_cost ≈ c_pv*dcap_pv + c_wind*dcap_wind + c_gas*dcap_gas
#                + c_batP*Pbat_total + c_batE*Ebat_total
# This keeps the decomposition aligned with the solved model outputs.
inv_cols = ["dcap_pv", "dcap_wind", "dcap_gas", "Pbat_total", "Ebat_total"]
if all(c in sens.columns for c in inv_cols + ["investment_cost"]):
    X = sens[inv_cols].to_numpy(dtype=float)
    y = sens["investment_cost"].to_numpy(dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)

    inv_comp_eur = np.array([
        coef[0] * float(base["dcap_pv"]),
        coef[1] * float(base["dcap_wind"]),
        coef[2] * float(base["dcap_gas"]),
        coef[3] * float(base["Pbat_total"]),
        coef[4] * float(base["Ebat_total"]),
    ], dtype=float)
    inv_comp_eur = np.clip(inv_comp_eur, 0.0, None)

    # Rescale to exact base investment total so labels sum cleanly.
    inv_total = float(base["investment_cost"])
    if inv_comp_eur.sum() > 1e-9:
        inv_comp_eur *= inv_total / inv_comp_eur.sum()

    inv_labels = ["PV build", "Wind build", "Gas build", "Battery power", "Battery energy"]
    inv_colors = [GOLD, BLUE, RED, GREEN, TEAL]
    inv_values_M = inv_comp_eur / 1e6

    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    bottom = 0.0
    for v, c, lab in zip(inv_values_M, inv_colors, inv_labels):
        ax.bar(0.5, v, bottom=bottom, color=c, width=0.45, label=lab, zorder=3)
        if v > 3:
            ax.text(0.5, bottom + v / 2, f"€{v:.1f}M", ha="center", va="center",
                    fontsize=7.5, color="white" if c in [RED, GREEN, TEAL] else INK,
                    fontweight="bold")
        bottom += v

    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_ylabel("Annual Investment Cost (M€/year)")
    ax.set_title("Base Case Investment Decomposition by Technology\n"
                 r"Oil 30% · VoLL €6,500/MWh · CO$_2$ €30/tCO$_2$",
                 pad=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0)
    ax.text(0.5, bottom + 3, f"Total investment: €{bottom:.1f}M", ha="center",
            fontsize=8.5, fontweight="bold", color=INK)
    ax.set_ylim(0, bottom * 1.14)
    ax.grid(axis="x", visible=False)
    savefig("fig01b_investment_decomposition_base.pdf")
else:
    warnings.warn("Skipping Fig 01b: missing investment build columns.")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 02 — Base Case Generation Mix (horizontal bar)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.2))

gen_labels = ["PV", "Wind", "Gas (CCGT)", "Oil", "Battery discharge"]
gen_vals   = [base["total_generation_pv"], base["total_generation_wind"],
              base["total_generation_gas"], base["total_generation_oil"],
              base["total_battery_discharge"]]
gen_vals_twh = [v / 1e6 for v in gen_vals]
gen_colors   = [GOLD, BLUE, RED, MUTED, GREEN]
gen_pcts     = [v / sum(gen_vals) * 100 for v in gen_vals]

bars = ax.barh(gen_labels, gen_vals_twh, color=gen_colors, zorder=3, height=0.55)
for bar, pct, val in zip(bars, gen_pcts, gen_vals_twh):
    ax.text(val + 0.04, bar.get_y() + bar.get_height() / 2,
            f"{val:.2f} TWh  ({pct:.1f}%)", va="center", fontsize=7.5)

ax.set_xlabel("Annual Generation (TWh/year)")
ax.set_title("Base Case Annual Generation Mix", pad=8)
ax.set_xlim(0, max(gen_vals_twh) * 1.45)
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
savefig("fig02_generation_mix_base.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 03 — Total Cost vs Carbon Tax (by oil factor)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 4.0))

oil_sel = [0.0, 0.10, 0.20, 0.30]
ls_list = ["-", "--", "-.", ":"]
for oil, ls, col in zip(oil_sel, ls_list, [RED, GOLD, GREEN, BLUE]):
    sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
    ax.plot(sub["carbon_tax"], sub["total_cost_M"],
            color=col, ls=ls, marker="o", label=f"Oil {int(oil*100)}%")

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Total Annual Cost (M€/year)")
ax.set_title(r"Total System Cost vs. Carbon Tax" + "\n" +
             r"(VoLL = €6,500/MWh, by oil availability factor)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
ax.legend(title="Oil avail.", framealpha=0.9)
savefig("fig03_cost_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 04 — Total Cost vs Oil Availability
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 4.0))

co2_sel = [0.0, 20.0, 40.0]
ls_list = ["-", "--", "-."]
for co2, ls, col in zip(co2_sel, ls_list, [GREEN, GOLD, RED]):
    sub = q(sens, voll=VOLL_BASE, co2=co2).sort_values("oil_factor")
    ax.plot(sub["oil_factor_pct"], sub["total_cost_M"],
            color=col, ls=ls, marker="s", label=f"CO₂ €{int(co2)}/t")

ax.set_xlabel("Oil Availability Factor (%)")
ax.set_ylabel("Total Annual Cost (M€/year)")
ax.set_title("Total System Cost vs. Oil Availability\n"
             r"(VoLL = €6,500/MWh, by carbon tax)", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
ax.legend(title="Carbon tax", framealpha=0.9)
savefig("fig04_cost_vs_oil.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 05 — New Capacity vs Carbon Tax (PV, Wind, CCGT, Battery)
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 4, figsize=(12.2, 3.8), sharey=False)
titles = ["New PV (MW)", "New Wind (MW)", "New CCGT (MW)", "Battery Energy (MWh)"]
cols_y = ["dcap_pv_MW", "dcap_wind_MW", "dcap_gas_MW", "bat_total_MWh"]

for ax, title, col in zip(axes, titles, cols_y):
    vals = []
    for oil, color in zip([0.0, 0.15, 0.30], [RED, GOLD, BLUE]):
        sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
        vals.extend(sub[col].tolist())
        ax.plot(sub["carbon_tax"], sub[col],
                color=color, marker="o", label=f"Oil {int(oil*100)}%")
    ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax.set_ylabel(title)
    ax.set_title(title, pad=6)
    if vals:
        ymin, ymax = min(vals), max(vals)
        span = ymax - ymin
        pad = 0.12 * span if span > 0 else max(1.0, 0.05 * abs(ymax))
        ax.set_ylim(ymin - pad, ymax + pad)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))

axes[0].legend(title="Oil avail.", fontsize=7.5)
fig.suptitle("Capacity Investment vs. Carbon Tax  (VoLL = €6,500/MWh)",
             fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig05_investment_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 06 — Battery Storage vs Carbon Tax (total MWh, by oil factor)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 4.0))

for oil, col, ls in zip([0.0, 0.10, 0.30], [RED, GOLD, BLUE], ["-", "--", "-."]):
    sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
    ax.plot(sub["carbon_tax"], sub["bat_total_MWh"],
            color=col, ls=ls, marker="^", label=f"Oil {int(oil*100)}%")

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Total Battery Energy Capacity (MWh)")
ax.set_title("Battery Storage Investment vs. Carbon Tax\n"
             r"(VoLL = €6,500/MWh, by oil availability)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(title="Oil avail.", framealpha=0.9)
savefig("fig06_battery_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 07 — Carbon Cost Component vs Tax Level (stacked bars: oil fracs)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))

x = np.arange(len(CO2_LEVELS))
width = 0.22
for i, (oil, col) in enumerate(zip([0.0, 0.10, 0.30], [RED, GOLD, BLUE])):
    sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
    rects = ax.bar(x + (i - 1) * width, sub["carbon_cost_M"],
                   width=width, color=col, alpha=0.85, label=f"Oil {int(oil*100)}%",
                   zorder=3)

ax.set_xticks(x)
ax.set_xticklabels([f"€{int(c)}" for c in CO2_LEVELS])
ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Carbon Cost Component (M€/year)")
ax.set_title(r"Carbon Tax Revenue Component vs. Tax Level" + "\n" +
             r"(VoLL = €6,500/MWh)", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
ax.legend(title="Oil avail.", framealpha=0.9)
savefig("fig07_carbon_cost_component.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 08 — Fuel Mix (Gas vs Oil TWh) vs Carbon Tax — two panels
# ─────────────────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=False)

for oil, col, ls in zip([0.0, 0.10, 0.30], [RED, GOLD, BLUE], ["-", "--", "-."]):
    sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
    ax1.plot(sub["carbon_tax"], sub["gen_gas_TWh"],
             color=col, ls=ls, marker="o", label=f"Oil {int(oil*100)}%")
    ax2.plot(sub["carbon_tax"], sub["gen_oil_TWh"] * 1000,
             color=col, ls=ls, marker="s", label=f"Oil {int(oil*100)}%")

for ax, ylabel, title in zip(
    [ax1, ax2],
    ["Annual Gas Generation (TWh)", "Annual Oil Generation (GWh)"],
    ["CCGT Dispatch vs. Carbon Tax", "Oil Dispatch vs. Carbon Tax"]
):
    ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=6)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
    ax.legend(title="Oil avail.", fontsize=7.5)

fig.suptitle(r"Fossil Fuel Dispatch vs. Carbon Tax  (VoLL = €6,500/MWh)",
             fontsize=10, y=1.02)
plt.tight_layout()
savefig("fig08_fuel_mix_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 09 — Curtailment Rate vs Carbon Tax
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 4.0))

for oil, col, ls in zip([0.0, 0.10, 0.30], [RED, GOLD, BLUE], ["-", "--", "-."]):
    sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
    ax.plot(sub["carbon_tax"], sub["curt_pct_of_potential"],
            color=col, ls=ls, marker="D", label=f"Oil {int(oil*100)}%")

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Curtailment Rate (% of potential renewable output)")
ax.set_title("Renewable Curtailment vs. Carbon Tax\n"
             r"(VoLL = €6,500/MWh)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
ax.legend(title="Oil avail.", framealpha=0.9)
savefig("fig09_curtailment_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 10 — Unserved Energy vs Carbon Tax (by VoLL, oil=0%)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 4.0))

voll_colors = {2000.0: RED, 6500.0: GOLD, 10000.0: GREEN}
voll_labels = {2000.0: "€2,000", 6500.0: "€6,500", 10000.0: "€10,000"}
for voll_val in VOLL_LEVELS:
    sub = q(sens, oil=0.0, voll=voll_val).sort_values("carbon_tax")
    ax.plot(sub["carbon_tax"], sub["total_nse_mwh"],
            color=voll_colors[voll_val], marker="o",
            label=f"VoLL = {voll_labels[voll_val]}/MWh")

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Unserved Energy (MWh/year)")
ax.set_title("Unserved Energy vs. Carbon Tax\n"
             "(Oil availability = 0%, by VoLL)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(title="VoLL", framealpha=0.9)
savefig("fig10_nse_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 11 — Oil Generation vs Oil Availability Factor
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))

for co2, col, ls in zip([0.0, 30.0, 50.0], [GREEN, GOLD, RED], ["-", "--", "-."]):
    sub = q(sens, voll=VOLL_BASE, co2=co2).sort_values("oil_factor")
    ax.plot(sub["oil_factor_pct"], sub["gen_oil_TWh"] * 1000,
            color=col, ls=ls, marker="o", label=f"CO₂ €{int(co2)}/t")

ax.set_xlabel("Oil Availability Factor (%)")
ax.set_ylabel("Annual Oil Generation (GWh/year)")
ax.set_title("Oil Dispatch vs. Oil Availability Factor\n"
             r"(VoLL = €6,500/MWh, by carbon tax)", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f} GWh"))
ax.legend(title="Carbon tax", framealpha=0.9)

# Annotate the "flat region"
ax.annotate("Flat region:\ndispatched only for\nsynchronous minimum",
            xy=(15, 34), xytext=(18, 12),
            fontsize=7, color=MUTED,
            arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))

savefig("fig11_oil_generation_vs_factor.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 12 — Investment Cost vs Oil Factor
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))

for co2, col, ls in zip([0.0, 30.0, 50.0], [GREEN, GOLD, RED], ["-", "--", "-."]):
    sub = q(sens, voll=VOLL_BASE, co2=co2).sort_values("oil_factor")
    ax.plot(sub["oil_factor_pct"], sub["invest_M"],
            color=col, ls=ls, marker="s", label=f"CO₂ €{int(co2)}/t")

ax.set_xlabel("Oil Availability Factor (%)")
ax.set_ylabel("Annualised Investment Cost (M€/year)")
ax.set_title("Investment Cost vs. Oil Availability Factor\n"
             r"(VoLL = €6,500/MWh, by carbon tax)", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))
ax.legend(title="Carbon tax", framealpha=0.9)
savefig("fig12_investment_cost_vs_oil.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 13 — Oil Phase-Down Summary (multi-panel: CF + invest cost + CCGT build)
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(10, 3.8))

sub30 = q(sens, voll=VOLL_BASE, co2=30.0).sort_values("oil_factor")
oil_cap = sub30["oil_factor"] * 1482.5

# Panel A: Oil capacity factor
# gen_oil_TWh is in TWh/year, so convert to MWh/year with 1e6 (not 1e3).
cf = sub30["gen_oil_TWh"] * 1e6 / (oil_cap.replace(0, np.nan) * 8760) * 100
axes[0].bar(sub30["oil_factor_pct"], cf.fillna(0), color=MUTED,
            zorder=3, width=3.5, edgecolor="white", linewidth=0.4)
axes[0].set_xlabel("Oil Availability (%)")
axes[0].set_ylabel("Oil Capacity Factor (%)")
axes[0].set_title("Oil Capacity Factor", pad=6)
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))

# Panel B: Investment cost
axes[1].plot(sub30["oil_factor_pct"], sub30["invest_M"],
             color=BLUE, marker="o", zorder=3)
axes[1].fill_between(sub30["oil_factor_pct"], sub30["invest_M"],
                     alpha=0.15, color=BLUE)
axes[1].set_xlabel("Oil Availability (%)")
axes[1].set_ylabel("Investment Cost (M€/year)")
axes[1].set_title("Investment Cost", pad=6)
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}M"))

# Panel C: New CCGT capacity
axes[2].bar(sub30["oil_factor_pct"], sub30["dcap_gas_MW"],
            color=RED, zorder=3, width=3.5, edgecolor="white", linewidth=0.4)
axes[2].set_xlabel("Oil Availability (%)")
axes[2].set_ylabel("New CCGT Capacity (MW)")
axes[2].set_title("New Gas (CCGT) Capacity", pad=6)

fig.suptitle(r"Oil Phase-Down Analysis  (CO$_2$ = €30/t, VoLL = €6,500/MWh)",
             fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig13_oil_phase_down.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 14 — Dispatch Profile: Representative Summer Week (base dispatch)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.5, 4.2))

# Pick first full week of July (high PV)
july = disp[disp["timestamp"].dt.month == 7].iloc[:168].copy()
t    = np.arange(len(july))

ax.stackplot(t,
             july["p_pv"],
             july["p_wind"],
             july["discharge_total"],
             july["p_oil"],
             july["p_gas"],
             labels=["PV", "Wind", "Battery discharge", "Oil", "Gas (CCGT)"],
             colors=[GOLD, BLUE, GREEN, MUTED, RED],
             alpha=0.88, zorder=2)

ax.plot(t, july["demand_mwh"], color=INK, lw=1.5, ls="--",
        label="Demand", zorder=4)

# Show curtailment as negative fill
curt = july["curt_pv"] + july["curt_wind"]
ax.fill_between(t, 0, -curt, color=GOLD, alpha=0.35, hatch="//",
                label="Curtailment (curtailed)")

# Charge as negative bars
ax.fill_between(t, 0, -july["charge_total"], color=GREEN, alpha=0.4,
                label="Battery charge (net load)")

ax.axhline(0, color=INK, lw=0.5)
ax.set_xlim(0, len(july) - 1)
ax.set_xticks(np.arange(0, 168, 24))
ax.set_xticklabels([f"Day {i+1}" for i in range(7)])
ax.set_xlabel("Hour of Week (first week of July)")
ax.set_ylabel("Power (MW)")
ax.set_title("Hourly Dispatch Profile — Representative Summer Week (Base Case)", pad=8)
ax.legend(ncol=4, fontsize=7.5, loc="upper right")
savefig("fig14_dispatch_profile_week.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 15 — Load Duration Curve + Renewable Generation Curve
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 4.0))

demand_sorted = np.sort(disp["demand_mwh"])[::-1]
pv_sorted     = np.sort(disp["p_pv"])[::-1]
wind_sorted   = np.sort(disp["p_wind"])[::-1]
h             = np.linspace(0, 100, len(demand_sorted))

ax.plot(h, demand_sorted, color=INK, lw=1.8, label="Demand (LDC)")
ax.plot(h, pv_sorted,     color=GOLD, lw=1.4, ls="--", label="PV output (base)")
ax.plot(h, wind_sorted,   color=BLUE, lw=1.4, ls="-.", label="Wind output (base)")
ax.fill_between(h, demand_sorted, alpha=0.06, color=INK)

ax.set_xlabel("Percentage of Year (%)")
ax.set_ylabel("Power (MW)")
ax.set_title("Load Duration Curve and Renewable Output Curves (Base Case)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(framealpha=0.9)

# Annotate peak demand
ax.annotate(f"Peak demand: {demand_sorted[0]:.0f} MW",
            xy=(0, demand_sorted[0]), xytext=(8, demand_sorted[0] * 0.96),
            fontsize=7.5, color=INK,
            arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))

savefig("fig15_duration_curve.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 16 — Cost–Emissions Pareto Frontier (base case feasible scenarios)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.0, 4.5))

# Only base case = feasible (nse_pct < 0.01) scenarios; vary carbon tax and oil
feasible = sens[(sens["nse_pct"] < 0.01) & (sens["voll"] == VOLL_BASE)].copy()

# Color by oil factor
oil_vals = sorted(feasible["oil_factor"].unique())
cmap     = mpl.cm.get_cmap("RdYlGn_r", len(oil_vals))
norm     = mpl.colors.BoundaryNorm(
               [f - 0.025 for f in oil_vals] + [oil_vals[-1] + 0.025],
               cmap.N)

sc = ax.scatter(feasible["implied_co2_Mt"],
                feasible["total_cost_M"],
                c=feasible["oil_factor"], cmap="RdYlGn_r",
                s=40, zorder=4, alpha=0.85, edgecolors="white", linewidths=0.4)

# Pareto frontier for oil=0.10 (baseline oil)
pf = feasible[feasible["oil_factor"] == 0.10].sort_values("implied_co2_Mt")
ax.plot(pf["implied_co2_Mt"], pf["total_cost_M"],
        color=BLUE, lw=1.6, ls="--", zorder=3, label="Pareto frontier (oil 10%)")

# Annotate carbon tax levels along the frontier
for _, row in pf.iterrows():
    ax.text(row["implied_co2_Mt"] + 0.003, row["total_cost_M"] + 0.5,
            f"€{int(row['carbon_tax'])}", fontsize=6.5, color=BLUE, va="bottom")

cb = fig.colorbar(sc, ax=ax, label="Oil Availability Factor", pad=0.02)
cb.set_ticks(oil_vals)
cb.set_ticklabels([f"{int(v*100)}%" for v in oil_vals])

ax.set_xlabel(r"Implied CO$_2$ Emissions (MtCO$_2$/year)")
ax.set_ylabel("Total System Cost (M€/year)")
ax.set_title(r"Cost–Emissions Pareto Frontier" + "\n" +
             r"(VoLL = €6,500/MWh, feasible scenarios only)", pad=8)
ax.legend(fontsize=8, loc="upper left")
savefig("fig16_cost_emissions_pareto.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 17 — Battery Duration Breakdown (base case: 2h / 4h / 8h split)
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8))

# By carbon tax (oil=10%, voll=6500)
sub = q(sens, oil=0.10, voll=VOLL_BASE).sort_values("carbon_tax")
x   = np.arange(len(sub))
w   = 0.26
axes[0].bar(x - w, sub["Ebat_2"], width=w, color=GREEN,  alpha=0.85, label="2h")
axes[0].bar(x,     sub["Ebat_4"], width=w, color=BLUE,   alpha=0.85, label="4h")
axes[0].bar(x + w, sub["Ebat_8"], width=w, color=RED,    alpha=0.85, label="8h")
axes[0].set_xticks(x)
axes[0].set_xticklabels([f"€{int(c)}" for c in sub["carbon_tax"]])
axes[0].set_xlabel(r"Carbon Tax (€/tCO$_2$)")
axes[0].set_ylabel("Battery Energy by Duration (MWh)")
axes[0].set_title("Battery Duration Split vs. Carbon Tax\n(Oil 10%, VoLL €6,500)", pad=6)
axes[0].legend(title="Duration")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

# By oil factor (carbon=30, voll=6500)
sub2 = q(sens, voll=VOLL_BASE, co2=30.0).sort_values("oil_factor")
x2   = np.arange(len(sub2))
axes[1].bar(x2 - w, sub2["Ebat_2"], width=w, color=GREEN,  alpha=0.85, label="2h")
axes[1].bar(x2,     sub2["Ebat_4"], width=w, color=BLUE,   alpha=0.85, label="4h")
axes[1].bar(x2 + w, sub2["Ebat_8"], width=w, color=RED,    alpha=0.85, label="8h")
axes[1].set_xticks(x2)
axes[1].set_xticklabels([f"{int(v*100)}%" for v in sub2["oil_factor"]])
axes[1].set_xlabel("Oil Availability Factor (%)")
axes[1].set_ylabel("Battery Energy by Duration (MWh)")
axes[1].set_title(r"Battery Duration Split vs. Oil Availability" + "\n" +
                  r"(CO$_2$ €30/t, VoLL €6,500)", pad=6)
axes[1].legend(title="Duration")
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

fig.suptitle("Battery Storage Investment by Duration Class", fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig17_battery_duration_split.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 18 — Dispatch Heatmap: PV output by hour-of-day × month
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))

disp["hour"]  = disp["timestamp"].dt.hour
disp["month"] = disp["timestamp"].dt.month

for ax, col, title, cmap in zip(
    axes,
    ["p_pv", "curt_pv", "soc_8"],
    ["PV Generation (MW)", "PV Curtailment (MW)", "8h Battery SOC (MWh)"],
    ["YlOrRd", "Reds", "Blues"]
):
    pivot = disp.pivot_table(values=col, index="hour", columns="month", aggfunc="mean")
    im = ax.imshow(pivot, aspect="auto", cmap=cmap, origin="upper")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hour of Day")
    ax.set_title(title, pad=6)
    ax.set_xticks(range(12))
    ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"], fontsize=7)
    ax.set_yticks(range(0, 24, 4))
    plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)

fig.suptitle("Seasonal-Diurnal Dispatch Heatmaps (Base Case)",
             fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig18_dispatch_heatmaps.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 19 — Sensitivity Tornado Chart (total cost impact of each dimension)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.5, 3.6))

# Measure swing in total cost along each axis, holding others at base
base_co2  = 30.0
base_oil  = 0.10
base_voll = VOLL_BASE

ranges = {}
# Carbon tax swing (oil=base, voll=base)
sub = q(sens, oil=base_oil, voll=base_voll)
ranges["Carbon Tax\n(€0 → €50/t)"] = (
    sub["total_cost_M"].min(), sub["total_cost_M"].max())

# Oil availability swing (co2=base, voll=base)
sub = q(sens, voll=base_voll, co2=base_co2)
ranges["Oil Availability\n(0% → 30%)"] = (
    sub["total_cost_M"].min(), sub["total_cost_M"].max())

# VoLL swing (oil=base, co2=base)
sub = q(sens, oil=base_oil, co2=base_co2)
ranges["Value of Lost Load\n(€2k → €10k/MWh)"] = (
    sub["total_cost_M"].min(), sub["total_cost_M"].max())

base_cost = q(sens, oil=base_oil, voll=base_voll, co2=base_co2)["total_cost_M"].values[0]
labels = list(ranges.keys())
lows   = [v[0] - base_cost for v in ranges.values()]
highs  = [v[1] - base_cost for v in ranges.values()]

y_pos = np.arange(len(labels))
ax.barh(y_pos, [h - l for l, h in zip(lows, highs)], left=lows,
        color=[RED if abs(h) > abs(l) else BLUE
               for l, h in zip(lows, highs)],
        alpha=0.8, zorder=3, height=0.45)

ax.axvline(0, color=INK, lw=1.0, zorder=5)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel("Change in Total System Cost vs. Base (M€/year)")
ax.set_title("Sensitivity Tornado Chart\n"
             r"(Base: oil 10%, CO$_2$ €30/t, VoLL €6,500/MWh)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"+€{x:.0f}M" if x > 0 else f"€{x:.0f}M"))

for i, (l, h) in enumerate(zip(lows, highs)):
    ax.text(l - 0.5, i, f"€{ranges[labels[i]][0]:.0f}M", ha="right", va="center",
            fontsize=7, color=MUTED)
    ax.text(h + 0.5, i, f"€{ranges[labels[i]][1]:.0f}M", ha="left",  va="center",
            fontsize=7, color=MUTED)

savefig("fig19_tornado_sensitivity.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 20 — Stacked Area: Generation mix vs Carbon Tax (oil=10%)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.5, 4.2))

sub = q(sens, oil=0.10, voll=VOLL_BASE).sort_values("carbon_tax")
x = sub["carbon_tax"].values
ax.stackplot(x,
             sub["gen_pv_TWh"],
             sub["gen_wind_TWh"],
             sub["gen_gas_TWh"] - sub["carbon_cost_M"] * 0,  # just gen
             sub["gen_oil_TWh"],
             labels=["PV", "Wind", "Gas (CCGT)", "Oil"],
             colors=[GOLD, BLUE, RED, MUTED],
             alpha=0.88)

total = sub["gen_pv_TWh"] + sub["gen_wind_TWh"] + sub["gen_gas_TWh"] + sub["gen_oil_TWh"]
ax.plot(x, total, color=INK, lw=1.2, ls="--", label="Total generation (incl. losses)", alpha=0.5)

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Annual Generation (TWh/year)")
ax.set_title("Generation Mix vs. Carbon Tax\n"
             r"(Oil 10%, VoLL = €6,500/MWh)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f} TWh"))
ax.legend(loc="upper right", fontsize=8)
savefig("fig20_generation_mix_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 21 — Base Case Installed Capacity: Before vs After (all techs together)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.8, 4.0))

techs = ["PV", "Wind", "Oil", "Gas", "Battery (P)"]
tech_colors = [GOLD, BLUE, MUTED, RED, GREEN]
bat_p_before = float(base["Pbat_before_total"]) if "Pbat_before_total" in sens.columns else 0.0
bat_p_after = float(base["Pbat_after_total"]) if "Pbat_after_total" in sens.columns else float(base["Pbat_total"])
before_vals = np.array([
    float(base["cap_exist_pv"]),
    float(base["cap_exist_wind"]),
    float(base["cap_exist_oil_full"]),
    float(base["cap_exist_gas"]),
    bat_p_before,
], dtype=float)
after_vals = np.array([
    float(base["cap_after_pv"]),
    float(base["cap_after_wind"]),
    float(base["cap_after_oil"]),
    float(base["cap_after_gas"]),
    bat_p_after,
], dtype=float)

x = np.arange(len(techs))
w = 0.36
b1 = ax.bar(x - w/2, before_vals, width=w, color="white", edgecolor=INK, hatch="//",
            linewidth=0.8, label="Existing", zorder=3)
b2 = ax.bar(x + w/2, after_vals, width=w, color=tech_colors, edgecolor="white",
            linewidth=0.5, label="Total after optimisation", zorder=3, alpha=0.95)

ax.set_xticks(x)
ax.set_xticklabels(techs)
ax.set_ylabel("Installed Capacity (MW)")
ax.set_title("Base Case Installed Capacity — Before vs After\n"
             r"Oil 30% · VoLL €6,500/MWh · CO$_2$ €30/tCO$_2$", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))
ax.legend(loc="upper left", ncol=2, fontsize=7.8, framealpha=0.95)

for rects in [b1, b2]:
    for r in rects:
        h = r.get_height()
        ax.text(r.get_x() + r.get_width() / 2, h + max(after_vals.max() * 0.01, 5),
                f"{h:.0f}", ha="center", va="bottom", fontsize=7, color=INK)

ax.set_ylim(0, max(after_vals.max(), before_vals.max()) * 1.18)
savefig("fig21_capacity_before_after_base.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 22 — Base Case Capacity Composition: Existing vs New Build
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.6, 4.0))

techs_comp = ["PV", "Wind", "Oil", "Gas"]
tech_colors_comp = [GOLD, BLUE, MUTED, RED]
x_comp = np.arange(len(techs_comp))
existing = before_vals[:4].copy()
new_build = np.array([
    float(base["newbuild_pv_MW"]),
    float(base["newbuild_wind_MW"]),
    float(base["newbuild_oil_MW"]),
    float(base["newbuild_gas_MW"]),
], dtype=float)

ax.bar(x_comp, existing, width=0.62, color="white", edgecolor=INK, hatch="//",
       linewidth=0.8, label="Existing", zorder=3)
ax.bar(x_comp, new_build, width=0.62, bottom=existing, color=tech_colors_comp, edgecolor="white",
       linewidth=0.5, label="New build", zorder=3, alpha=0.95)

ax.set_xticks(x_comp)
ax.set_xticklabels(techs_comp)
ax.set_ylabel("Installed Capacity (MW)")
ax.set_title("Base Case Capacity Composition — Existing vs New Build", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))
ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
ax.set_ylim(0, (existing + new_build).max() * 1.18)
savefig("fig22_capacity_composition_base.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 23 — Base Case Battery Capacity: Before vs After
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.8))

bat_p_before = float(base["Pbat_before_total"]) if "Pbat_before_total" in sens.columns else 0.0
bat_e_before = float(base["Ebat_before_total"]) if "Ebat_before_total" in sens.columns else 0.0
bat_p_after = float(base["Pbat_after_total"]) if "Pbat_after_total" in sens.columns else float(base["Pbat_total"])
bat_e_after = float(base["Ebat_after_total"]) if "Ebat_after_total" in sens.columns else float(base["Ebat_total"])

for ax, vals, ylabel, title in zip(
    axes,
    [[bat_p_before, bat_p_after], [bat_e_before, bat_e_after]],
    ["Battery Power Capacity (MW)", "Battery Energy Capacity (MWh)"],
    ["Power capacity", "Energy capacity"],
):
    bars = ax.bar(["Before", "After"], vals, color=["white", GREEN], edgecolor=[INK, "white"],
                  hatch=["//", ""], linewidth=0.8, zorder=3, alpha=0.95)
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width()/2, h + max(vals) * 0.04 + 0.8, f"{h:.0f}",
                ha="center", va="bottom", fontsize=7)
    ax.set_ylim(0, max(vals) * 1.28 + 1)

fig.suptitle("Base Case Battery Capacity — Before vs After", fontsize=10, y=1.02)
plt.tight_layout()
savefig("fig23_battery_capacity_before_after_base.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 24 — Total Installed Capacity vs Carbon Tax (oil=10%, VoLL=6500)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.3, 4.0))

sub = q(sens, oil=0.10, voll=VOLL_BASE).sort_values("carbon_tax")
ax.plot(sub["carbon_tax"], sub["cap_after_pv"],   color=GOLD, marker="o", label="PV")
ax.plot(sub["carbon_tax"], sub["cap_after_wind"], color=BLUE, marker="o", label="Wind")
ax.plot(sub["carbon_tax"], sub["cap_after_oil"],  color=MUTED, marker="o", label="Oil")
ax.plot(sub["carbon_tax"], sub["cap_after_gas"],  color=RED, marker="o", label="Gas (CCGT)")

ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
ax.set_ylabel("Total Installed Capacity (MW)")
ax.set_title("Total Installed Capacity vs Carbon Tax\n(Oil 10%, VoLL = €6,500/MWh)", pad=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.legend(ncol=2, fontsize=8, framealpha=0.95)
savefig("fig24_total_capacity_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 25 — Total Installed Capacity vs Oil Availability (CO2=30, VoLL=6500)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.3, 4.0))

sub = q(sens, voll=VOLL_BASE, co2=30.0).sort_values("oil_factor")
ax.plot(sub["oil_factor_pct"], sub["cap_after_pv"],   color=GOLD, marker="s", label="PV")
ax.plot(sub["oil_factor_pct"], sub["cap_after_wind"], color=BLUE, marker="s", label="Wind")
ax.plot(sub["oil_factor_pct"], sub["cap_after_oil"],  color=MUTED, marker="s", label="Oil")
ax.plot(sub["oil_factor_pct"], sub["cap_after_gas"],  color=RED, marker="s", label="Gas (CCGT)")

ax.set_xlabel("Oil Availability Factor (%)")
ax.set_ylabel("Total Installed Capacity (MW)")
ax.set_title(r"Total Installed Capacity vs Oil Availability" + "\n" +
             r"(CO$_2$ = €30/t, VoLL = €6,500/MWh)", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.legend(ncol=2, fontsize=8, framealpha=0.95)
savefig("fig25_total_capacity_vs_oil.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 26 — Base Case Capacity Factor by Technology
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.4, 4.0))

hours_year = 8760.0
cf_labels = ["PV", "Wind", "Oil", "Gas (CCGT)"]
cf_colors = [GOLD, BLUE, MUTED, RED]
gen_mwh = np.array([
    float(base["total_generation_pv"]),
    float(base["total_generation_wind"]),
    float(base["total_generation_oil"]),
    float(base["total_generation_gas"]),
], dtype=float)
cap_mw = np.array([
    float(base["cap_after_pv"]),
    float(base["cap_after_wind"]),
    float(base["cap_after_oil"]),
    float(base["cap_after_gas"]),
], dtype=float)

cf_pct = np.where(cap_mw > 1e-9, 100.0 * gen_mwh / (cap_mw * hours_year), np.nan)
x_cf = np.arange(len(cf_labels))
bars = ax.bar(x_cf, cf_pct, color=cf_colors, edgecolor="white", linewidth=0.5, zorder=3, width=0.62)

ax.set_xticks(x_cf)
ax.set_xticklabels(cf_labels)
ax.set_ylabel("Capacity Factor (%)")
ax.set_title("Base Case Capacity Factor by Technology\n"
             r"(Annual generation / (installed MW × 8760 h))", pad=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.0f}%"))
ax.set_ylim(0, max(np.nanmax(cf_pct), 1.0) * 1.2)

for i, b in enumerate(bars):
    val = cf_pct[i]
    if np.isfinite(val):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.9,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=INK,
        )
        ax.text(
            b.get_x() + b.get_width() / 2,
            1.2,
            f"{gen_mwh[i] / 1e6:.2f} TWh",
            ha="center",
            va="bottom",
            fontsize=6.8,
            color=MUTED,
            rotation=90,
        )

savefig("fig26_base_capacity_factor.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 27 — Zero-Oil Scenarios: Cost and Reliability vs Carbon Tax
# ─────────────────────────────────────────────────────────────────────────────
oil0 = q(sens, oil=0.0)
if oil0.empty:
    warnings.warn("No oil_factor=0.0 scenarios found. Skipping oil0 analysis figures.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.9))

    for voll in VOLL_LEVELS:
        sub = q(sens, oil=0.0, voll=voll).sort_values("carbon_tax")
        if len(sub) == 0:
            continue
        col = voll_colors.get(voll, INK) if "voll_colors" in globals() else INK
        ax1.plot(sub["carbon_tax"], sub["total_cost_M"], marker="o", color=col,
                 label=f"VoLL €{int(voll):,}/MWh")
        ax2.plot(sub["carbon_tax"], sub["nse_pct"], marker="o", color=col,
                 label=f"VoLL €{int(voll):,}/MWh")

    ax1.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax1.set_ylabel("Total Cost (M€/year)")
    ax1.set_title("Oil = 0%: Total Cost")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}M"))
    ax1.legend(fontsize=7.2, framealpha=0.95)

    ax2.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax2.set_ylabel("NSE (% of demand)")
    ax2.set_title("Oil = 0%: Reliability")
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.3f}%"))

    fig.suptitle("Zero-Oil Scenario Performance", fontsize=10, y=1.02)
    plt.tight_layout()
    savefig("fig27_oil0_cost_reliability_vs_carbon.pdf")

    # ─────────────────────────────────────────────────────────────────────────
    # FIG 28 — Is Oil=0 Worth It? Cost Premium vs Emissions Avoided
    # Benchmark: same (VoLL, carbon tax) at oil_factor = 30%
    # ─────────────────────────────────────────────────────────────────────────
    oil30 = q(sens, oil=0.30)
    cmp_cols = ["voll", "carbon_tax", "total_cost_M", "implied_co2_Mt", "nse_pct"]
    cmp = pd.merge(
        oil0[cmp_cols],
        oil30[cmp_cols],
        on=["voll", "carbon_tax"],
        suffixes=("_oil0", "_oil30"),
        how="inner",
    )

    if len(cmp) == 0:
        warnings.warn("No matching oil=0 and oil=30 scenario pairs found. Skipping Fig 28-29.")
    else:
        cmp["cost_premium_M"] = cmp["total_cost_M_oil0"] - cmp["total_cost_M_oil30"]
        cmp["co2_avoided_Mt"] = cmp["implied_co2_Mt_oil30"] - cmp["implied_co2_Mt_oil0"]
        cmp["nse_delta_pct"] = cmp["nse_pct_oil0"] - cmp["nse_pct_oil30"]
        cmp["abatement_eur_per_t"] = np.where(
            cmp["co2_avoided_Mt"] > 1e-9,
            cmp["cost_premium_M"] / cmp["co2_avoided_Mt"],   # M€/Mt = €/t
            np.nan,
        )

        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        norm = mpl.colors.Normalize(vmin=min(CO2_LEVELS), vmax=max(CO2_LEVELS))
        marker_map = {2000.0: "o", 6500.0: "s", 10000.0: "^"}

        for voll in sorted(cmp["voll"].unique()):
            sub = cmp[cmp["voll"] == voll]
            ax.scatter(
                sub["co2_avoided_Mt"],
                sub["cost_premium_M"],
                c=sub["carbon_tax"],
                cmap="RdYlGn_r",
                norm=norm,
                marker=marker_map.get(voll, "o"),
                s=42,
                edgecolors="white",
                linewidths=0.4,
                alpha=0.9,
                zorder=4,
            )

        cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap="RdYlGn_r"), ax=ax, pad=0.02)
        cb.set_label(r"Carbon Tax (€/tCO$_2$)")
        ax.axhline(0, color=INK, lw=0.9, ls="--")
        ax.axvline(0, color=INK, lw=0.9, ls="--")
        ax.set_xlabel(r"CO$_2$ Avoided vs Oil 30% (MtCO$_2$/year)")
        ax.set_ylabel("Cost Premium of Oil=0 (M€/year)")
        ax.set_title("Is Oil=0 Worth It? Cost vs Emissions Trade-off", pad=8)

        leg = [
            Line2D([0], [0], marker=marker_map.get(v, "o"), color="w",
                   markerfacecolor=INK, markeredgecolor="white",
                   markersize=6, label=f"VoLL €{int(v):,}/MWh")
            for v in sorted(cmp["voll"].unique())
        ]
        ax.legend(handles=leg, loc="upper left", fontsize=7.4, framealpha=0.95)
        savefig("fig28_oil0_worth_it_tradeoff.pdf")

        # ─────────────────────────────────────────────────────────────────────
        # FIG 29 — Oil=0 Abatement Cost vs Carbon Tax
        # ─────────────────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        for voll, col, ls in zip([2000.0, 6500.0, 10000.0], [RED, GOLD, BLUE], ["-", "--", "-."]):
            sub = cmp[cmp["voll"] == voll].sort_values("carbon_tax")
            if len(sub) == 0:
                continue
            ax.plot(
                sub["carbon_tax"],
                sub["abatement_eur_per_t"],
                color=col,
                ls=ls,
                marker="o",
                label=f"VoLL €{int(voll):,}/MWh",
            )

        ax.axhline(0, color=INK, lw=0.9, ls="--")
        ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
        ax.set_ylabel(r"Implicit Abatement Cost of Oil=0 (€/tCO$_2$)")
        ax.set_title("Oil=0 Scenario Value-for-Money", pad=8)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
        ax.legend(fontsize=7.4, framealpha=0.95)
        savefig("fig29_oil0_abatement_cost_vs_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 30 — Three Lowest Oil Scenarios: Cost + Reliability vs Carbon Tax
# ─────────────────────────────────────────────────────────────────────────────
low_oils = sorted(sens["oil_factor"].unique())[:3]
if len(low_oils) < 3:
    warnings.warn("Fewer than 3 oil-factor levels found. Skipping low-oil comparison figures.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.9))
    low_colors = [RED, GOLD, BLUE]
    low_styles = ["-", "--", "-."]

    for oil, col, ls in zip(low_oils, low_colors, low_styles):
        sub = q(sens, oil=oil, voll=VOLL_BASE).sort_values("carbon_tax")
        if len(sub) == 0:
            continue
        lab = f"Oil {int(oil*100)}%"
        ax1.plot(sub["carbon_tax"], sub["total_cost_M"], color=col, ls=ls, marker="o", label=lab)
        ax2.plot(sub["carbon_tax"], sub["nse_pct"], color=col, ls=ls, marker="o", label=lab)

    ax1.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax1.set_ylabel("Total Cost (M€/year)")
    ax1.set_title("Three Lowest Oil Levels: Total Cost")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}M"))
    ax1.legend(fontsize=7.6, framealpha=0.95)

    ax2.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax2.set_ylabel("NSE (% of demand)")
    ax2.set_title("Three Lowest Oil Levels: Reliability")
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:.0f}"))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.3f}%"))

    fig.suptitle("Low-Oil Comparison (Oil 0%, 5%, 10%) at VoLL €6,500/MWh", fontsize=10, y=1.02)
    plt.tight_layout()
    savefig("fig30_lowoil_cost_reliability_vs_carbon.pdf")

    # ─────────────────────────────────────────────────────────────────────────
    # FIG 31 — Are Lower-Oil Cases Worth It? (vs Oil 10% baseline)
    # ─────────────────────────────────────────────────────────────────────────
    oil_ref = low_oils[-1]  # typically 10%
    ref = q(sens, oil=oil_ref, voll=VOLL_BASE)[
        ["carbon_tax", "total_cost_M", "implied_co2_Mt", "nse_pct"]
    ].copy()

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    marker_map = {low_oils[0]: "o", low_oils[1]: "s"}
    color_map = {low_oils[0]: RED, low_oils[1]: BLUE}

    for oil in low_oils[:-1]:
        case = q(sens, oil=oil, voll=VOLL_BASE)[
            ["carbon_tax", "total_cost_M", "implied_co2_Mt", "nse_pct"]
        ].copy()
        cmp = pd.merge(case, ref, on="carbon_tax", suffixes=("_case", "_ref"), how="inner")
        if len(cmp) == 0:
            continue
        cmp["cost_premium_M"] = cmp["total_cost_M_case"] - cmp["total_cost_M_ref"]
        cmp["co2_avoided_Mt"] = cmp["implied_co2_Mt_ref"] - cmp["implied_co2_Mt_case"]
        cmp["abatement_eur_per_t"] = np.where(
            cmp["co2_avoided_Mt"] > 1e-9,
            cmp["cost_premium_M"] / cmp["co2_avoided_Mt"],   # M€/Mt = €/t
            np.nan,
        )

        ax.plot(
            cmp["co2_avoided_Mt"],
            cmp["cost_premium_M"],
            color=color_map.get(oil, INK),
            marker=marker_map.get(oil, "o"),
            ls="-",
            label=f"Oil {int(oil*100)}% vs {int(oil_ref*100)}%",
            zorder=4,
        )
        for _, r in cmp.iterrows():
            ax.text(r["co2_avoided_Mt"] + 0.001, r["cost_premium_M"] + 0.15,
                    f"€{int(r['carbon_tax'])}", fontsize=6.5, color=MUTED)

    ax.axhline(0, color=INK, lw=0.9, ls="--")
    ax.axvline(0, color=INK, lw=0.9, ls="--")
    ax.set_xlabel(r"CO$_2$ Avoided vs Oil 10% (MtCO$_2$/year)")
    ax.set_ylabel("Cost Premium vs Oil 10% (M€/year)")
    ax.set_title("Are Lower-Oil Scenarios Worth It?\n(VoLL €6,500/MWh)", pad=8)
    ax.legend(fontsize=7.5, framealpha=0.95, loc="upper left")
    savefig("fig31_lowoil_worth_it_vs_oil10.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 32 — Base Case Curtailment: Monthly profile with generation context
# ─────────────────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.2, 6.0), sharex=True)

disp_m = disp.copy()
disp_m["month"] = disp_m["timestamp"].dt.month
weights = disp_m["weight"] if "weight" in disp_m.columns else 1.0
month_index = pd.Index(range(1, 13), name="month")
month_lbl = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

monthly_pv = (disp_m["p_pv"] * weights).groupby(disp_m["month"]).sum().reindex(month_index, fill_value=0.0)
monthly_wind = (disp_m["p_wind"] * weights).groupby(disp_m["month"]).sum().reindex(month_index, fill_value=0.0)
monthly_oil = (disp_m["p_oil"] * weights).groupby(disp_m["month"]).sum().reindex(month_index, fill_value=0.0)
monthly_gas = (disp_m["p_gas"] * weights).groupby(disp_m["month"]).sum().reindex(month_index, fill_value=0.0)
monthly_curt = ((disp_m["curt_pv"] + disp_m["curt_wind"]) * weights).groupby(disp_m["month"]).sum().reindex(month_index, fill_value=0.0)

monthly_pv_gwh = monthly_pv / 1e3
monthly_wind_gwh = monthly_wind / 1e3
monthly_oil_gwh = monthly_oil / 1e3
monthly_gas_gwh = monthly_gas / 1e3
monthly_curt_gwh = monthly_curt / 1e3

xm = np.arange(12)
ax1.bar(xm, monthly_pv_gwh.values, color=GOLD, label="PV", width=0.72, zorder=3)
ax1.bar(xm, monthly_wind_gwh.values, bottom=monthly_pv_gwh.values, color=BLUE, label="Wind", width=0.72, zorder=3)
ax1.bar(xm, monthly_gas_gwh.values, bottom=(monthly_pv_gwh + monthly_wind_gwh).values,
        color=RED, label="Gas (CCGT)", width=0.72, zorder=3)
ax1.bar(xm, monthly_oil_gwh.values, bottom=(monthly_pv_gwh + monthly_wind_gwh + monthly_gas_gwh).values,
        color=MUTED, label="Oil", width=0.72, zorder=3)
ax1.set_ylabel("Generation (GWh/month)")
ax1.set_title("Base Case Monthly Generation by Technology", pad=6)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}"))
ax1.legend(ncol=4, fontsize=7.5, loc="upper left", framealpha=0.95)

ren_potential = monthly_pv + monthly_wind + monthly_curt
monthly_curt_rate = np.where(ren_potential > 1e-9, 100.0 * monthly_curt / ren_potential, np.nan)
annual_curt_gwh = float(monthly_curt.sum() / 1e3)
annual_curt_rate = float(100.0 * monthly_curt.sum() / ren_potential.sum()) if ren_potential.sum() > 1e-9 else np.nan

ax2.bar(xm, monthly_curt_gwh.values, color=GOLD, alpha=0.35, edgecolor=GOLD,
        hatch="//", label="Curtailment", width=0.72, zorder=3)
ax2.set_ylabel("Curtailment (GWh/month)")
ax2.set_title("Base Case Curtailment by Month", pad=6)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}"))

ax2b = ax2.twinx()
ax2b.plot(xm, monthly_curt_rate, color=INK, marker="o", lw=1.2, label="Curtailment rate")
ax2b.set_ylabel("Curtailment rate (% of RE potential)")
ax2b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))

ax2.text(
    0.01, 0.95,
    f"Annual curtailed energy: {annual_curt_gwh:.1f} GWh\nAnnual curtailment rate: {annual_curt_rate:.2f}%",
    transform=ax2.transAxes, ha="left", va="top",
    fontsize=7.4, color=INK,
    bbox=dict(facecolor="white", edgecolor=RULE, alpha=0.92, pad=2.5),
)

ax2.set_xticks(xm)
ax2.set_xticklabels(month_lbl)
ax2.set_xlabel("Month")

h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax2b.get_legend_handles_labels()
ax2.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=7.4, framealpha=0.95)

fig.suptitle("Base Case Curtailment and Generation Context", fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig32_base_curtailment_monthly.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 33 — Heatmap: Total Cost by VoLL, Oil Availability, and Carbon Tax
# ─────────────────────────────────────────────────────────────────────────────
voll_vals = sorted(sens["voll"].unique())
oil_vals_pct = sorted(sens["oil_factor_pct"].unique())
co2_vals = sorted(sens["carbon_tax"].unique())

heatmaps = []
for voll in voll_vals:
    grid = q(sens, voll=voll).pivot_table(
        values="total_cost_M",
        index="oil_factor_pct",
        columns="carbon_tax",
        aggfunc="mean",
    ).reindex(index=oil_vals_pct, columns=co2_vals)
    heatmaps.append(grid)

vmin = min(np.nanmin(h.values) for h in heatmaps)
vmax = max(np.nanmax(h.values) for h in heatmaps)

fig, axes = plt.subplots(1, len(voll_vals), figsize=(4.0 * len(voll_vals), 4.2), sharey=True)
axes = np.atleast_1d(axes)

for ax, voll, grid in zip(axes, voll_vals, heatmaps):
    im = ax.imshow(grid.values, aspect="auto", origin="lower", cmap="YlOrRd", vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(len(co2_vals)))
    ax.set_xticklabels([f"€{int(v)}" for v in co2_vals], rotation=30)
    ax.set_yticks(np.arange(len(oil_vals_pct)))
    ax.set_yticklabels([f"{v:.0f}%" for v in oil_vals_pct])
    ax.set_xlabel(r"Carbon Tax (€/tCO$_2$)")
    ax.set_title(f"VoLL €{int(voll):,}/MWh", pad=6)

    # Mark the minimum-cost cell in each VoLL panel.
    if np.isfinite(grid.values).any():
        iy, ix = np.unravel_index(np.nanargmin(grid.values), grid.values.shape)
        ax.scatter(ix, iy, marker="o", s=28, facecolors="none", edgecolors=INK, linewidths=1.0, zorder=4)

axes[0].set_ylabel("Oil Availability Factor (%)")
cbar = fig.colorbar(im, ax=axes.ravel().tolist(), pad=0.02)
cbar.set_label("Total Annual Cost (M€/year)")
fig.suptitle("Total Cost Heatmap: VoLL × Oil Availability × Carbon Tax", fontsize=10, y=1.02)
plt.tight_layout()
savefig("fig33_cost_heatmap_voll_oil_carbon.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 34 — Build Decision Ranges (box plots across all scenarios)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 1, figsize=(6.8, 4.0))

mw_specs = [
    ("dcap_pv_MW", "PV build"),
    ("dcap_wind_MW", "Wind build"),
    ("dcap_gas_MW", "Gas build"),
    ("Pbat_total", "Battery P"),
]
mw_colors = [GOLD, BLUE, RED, GREEN]
mw_data = [sens[c].dropna().values for c, _ in mw_specs if c in sens.columns]
mw_labels = [l for c, l in mw_specs if c in sens.columns]
mw_base = [float(base[c]) for c, _ in mw_specs if c in base.index]
box_rows = []
for c, label in mw_specs:
    if c not in sens.columns:
        continue
    arr = sens[c].dropna().astype(float).values
    if arr.size == 0:
        continue
    box_rows.append({
        "decision": label,
        "column": c,
        "units": "MW",
        "min": float(np.nanmin(arr)),
        "p25": float(np.nanpercentile(arr, 25)),
        "median": float(np.nanmedian(arr)),
        "p75": float(np.nanpercentile(arr, 75)),
        "max": float(np.nanmax(arr)),
        "mean": float(np.nanmean(arr)),
        "base_case": float(base[c]) if c in base.index else np.nan,
    })

if len(box_rows) > 0:
    table34 = pd.DataFrame(box_rows)
    table34_path = os.path.join(OUT_DIR, "table34_build_decision_ranges.csv")
    table34.to_csv(table34_path, index=False)
    print("  ✓  table34_build_decision_ranges.csv")

if len(mw_data) > 0:
    b = ax.boxplot(mw_data, labels=mw_labels, patch_artist=True, widths=0.62)
    for patch, col in zip(b["boxes"], mw_colors[:len(mw_data)]):
        patch.set_facecolor(col)
        patch.set_alpha(0.35)
        patch.set_edgecolor(col)
    for med in b["medians"]:
        med.set_color(INK)
        med.set_linewidth(1.2)
    for w in b["whiskers"] + b["caps"]:
        w.set_color(MUTED)
    for i, v in enumerate(mw_base):
        ax.scatter(i + 1, v, marker="D", s=30, color=INK, zorder=4)
    ax.set_ylabel("Build decision range (MW)")
    ax.set_title("Generation + Battery Power Builds")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.tick_params(axis="x", rotation=18)

fig.suptitle("Ranges of Build Decisions Across Sensitivity Scenarios", fontsize=10, y=1.01)
plt.tight_layout()
savefig("fig34_build_decision_ranges_boxplot.pdf")

print(f"\n✓  All figures saved to {OUT_DIR}")
print(f"   PDF + PNG pairs generated for each figure.")
