# Power Planning Model Runner

This folder contains the main model runner for annual investment + hourly dispatch planning.

## What the model does

- Co-optimizes yearly investment and hourly operation.
- Investment decisions:
  - `dcap_pv`, `dcap_wind`, `dcap_gas`
  - battery power/energy by duration `H = [2, 4, 8]`
- Hourly operation decisions:
  - `p_pv`, `p_wind`, `curt_pv`, `curt_wind`
  - `p_oil`, `p_gas`
  - `charge[h,t]`, `discharge[h,t]`, `soc[h,t]`
  - `nse[t]`, `reserve_shortfall[t]`
- Core constraints:
  - energy balance
  - renewable availability split (generation + curtailment)
  - generation capacity limits
  - storage SOC dynamics and cyclic condition
  - storage charge/discharge bounds
  - ramp limits
  - minimum synchronous requirement
  - reserve headroom requirement with slack
- Objective:
  - `investment_cost + operating_cost`

## Input CSV requirements

Required columns (alias matching is supported):

- `timestamp` (or `year` + `hour_of_year`)
- demand: `demand2030` / `demand_mwh_2030` / `demand_mwh` / `demand_MWh` / `demand` / `demand2019`
- PV availability: `pv_cf` / `pvCF` / `pv_cf_hourly`
- wind availability: `wind_cf` / `windCF` / `wind_cf_hourly`
- optional: `weight` (defaults to `1.0`)

Validation is intentionally direct:
- required columns must exist
- numeric columns must parse as numeric

## Self-contained package

Everything needed to run this model is inside this folder:

- model code (`*.jl`)
- Julia environment (`Project.toml`, `Manifest.toml`)
- default input data (`data/timeseries_2019_2030_scaled.csv`)
- outputs folder (`outputs/`)

## How to run

From repo root:

Base case:

```bash
julia --project=model model/run_base.jl
```

Sensitivity sweep:

```bash
julia --project=model model/run_sensitivity.jl
```

Or from inside `model/`:

```bash
cd model
julia --project=. run_base.jl
julia --project=. run_sensitivity.jl
```

Optional input path override:

```bash
julia --project=model model/run_base.jl model/data/myfile.csv
julia --project=model model/run_sensitivity.jl model/data/myfile.csv
```

Default input path:

- `model/data/timeseries_2019_2030_scaled.csv`
- If that file is not present, the runner selects a CSV from `model/data/`
  (prefers filenames containing `2030` and `scaled`).

## Sensitivity dimensions

- Oil availability factor: `0.00, 0.05, ..., 0.30`
- VoLL grid: `2000, 6500, 10000`
- Carbon tax grid: `0, 10, 20, 30, 40, 50`

Scenario naming:

- `base_oil{oil_factor}_voll{voll}_co2{carbon_tax}`
- Example: `base_oil0.15_voll6500_co230`

## Outputs written to `model/outputs/`

Base run:

- `base_results.csv` (single-row KPI table)
- `base_dispatch.csv` (hourly dispatch)

Sensitivity run:

- `sensitivity_results.csv` (one row per scenario)

Sensitivity mode writes a single combined summary table (no per-scenario dispatch files).

Plotting (single plotting script):

```bash
python model/plot_cyprus_results.py
```

This script reads `model/outputs/base_dispatch.csv` and `model/outputs/sensitivity_results.csv`
and writes figures to `model/outputs/figures/`.

## Where to change assumptions and grids

Edit `model/params.jl`:

- `OIL_FACTOR_LEVELS`
- `VOLL_GRID`
- `CARBON_TAX_GRID`
- `DEFAULT_OIL_FACTOR`, `DEFAULT_VOLL`, `DEFAULT_CARBON_TAX`
- all technology-cost, efficiency, ramp, and penalty assumptions

## File map

- `params.jl`: scenario grids, constants, derived costs, parameter builder
- `io.jl`: CSV loading and validation
- `model.jl`: JuMP variables, constraints, and objective
- `outputs.jl`: KPI extraction, dispatch export, terminal summaries
- `run_base.jl`: base case run
- `run_sensitivity.jl`: full sensitivity sweep
- `plot_cyprus_results.py`: figure pack for the paper
