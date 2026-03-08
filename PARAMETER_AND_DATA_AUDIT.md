# Parameter and Data Audit

## 1. Purpose
This document records the origin, interpretation, processing, and verification status of the core parameters and datasets used by this repository's planning model. It is intended to support reproducibility, transparent assumption tracking, and source verification for research use.

## 2. Repository structure for reproducibility
- `README.md`: high-level project scope, run instructions, and model interface overview.
- `params.jl`: canonical source of parameter values, scenario grids, and transformation formulas.
- `io.jl`: input schema, column alias handling, and validation/parsing logic for time-series data.
- `run_base.jl`: executes one base-case model run and writes base outputs.
- `run_sensitivity.jl`: executes full scenario sweep across oil-factor, VoLL, and carbon-tax grids.
- `outputs.jl`: transforms model solution values into reproducible CSV outputs/KPIs.
- `PARAMETER_AND_DATA_AUDIT.md`: detailed provenance, derivations, and source-status ledger.

## 3. Core parameter audit
| Category | Code name | Description | Value | Unit | Source | Calculation / derivation | Status |
|---|---|---|---|---|---|---|---|
| Discounting / financial assumptions | `DISCOUNT_RATE` | Social discount rate used in annualisation | `0.04` | - | EC SWD(2021)429, EUR-Lex CELEX:52021SC0429 (<https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52021SC0429>) | Direct constant | Documented |
| Unit conversion | `BTU_TO_KWH` | BTU to kWh conversion constant | `0.00029307107` | kWh/BTU | Standard physical conversion | Direct constant | Documented |
| Scenario assumptions | `BATTERY_DURATIONS` | Battery duration options for storage investment | `[2, 4, 8]` | h | ASSUMPTION | Discrete modelling design choice | Assumption |
| Scenario assumptions | `OIL_FACTOR_LEVELS` | Oil availability factors in sensitivity sweep | `0.00:0.05:0.30` | fraction of oil capacity | ASSUMPTION | Scenario grid | Assumption |
| Scenario assumptions | `VOLL_GRID` | VoLL values in sensitivity sweep | `[2000, 6500, 10000]` | EUR/MWh | Mixed: baseline from Zachariadis & Poullikkas, *Energy Policy* 51 (2012) 630-641; extremes are ASSUMPTION for variation | Scenario grid | Documented |
| Scenario assumptions | `CARBON_TAX_GRID` | Carbon tax values in sensitivity sweep | `0:10:50` | EUR/tCO2 | ASSUMPTION (policy scenario) | Scenario grid | Assumption |
| Base-case policy assumptions | `DEFAULT_OIL_FACTOR` | Default oil availability factor for base run | `0.30` | fraction | ASSUMPTION | Default selector from grid | Assumption |
| Base-case policy assumptions | `DEFAULT_VOLL` | Default VoLL for base run | `6500` | EUR/MWh | Zachariadis & Poullikkas, *The costs of power outages: A case study from Cyprus*, *Energy Policy* 51 (2012) 630-641 | Default selector from grid | Documented |
| Base-case policy assumptions | `DEFAULT_CARBON_TAX` | Default carbon tax for base run | `30` | EUR/tCO2 | ASSUMPTION | Default selector from grid | Assumption |
| Existing capacity assumptions | `pv_commercial_mw` | Existing commercial PV | `358.4` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `pv_self_consumption_excl_metering_mw` | Existing self-consumption PV excl. net-metering | `59.24` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `pv_own_use_mw` | Existing own-use PV | `2.08` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `pv_net_metering_mw` | Existing net-metering PV | `239.8` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `cap_exist_pv` | Existing total PV capacity used in model | `659.52` | MW | DERIVED | `pv_commercial + pv_self_consumption_excl_metering + pv_own_use + pv_net_metering` | Derived |
| Existing capacity assumptions | `cap_exist_wind_mw` | Existing wind capacity | `157.5` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `cap_exist_oil_mw` | Existing oil capacity (base before oil_factor scaling) | `1482.5` | MW | Cyprus - Final updated NECP 2021-2030 (submitted in 2024), European Commission publication page: <https://commission.europa.eu/publications/cyprus-final-updated-necp-2021-2030-submitted-2024_en> | Direct input | Documented |
| Existing capacity assumptions | `cap_exist_gas_mw` | Existing gas capacity represented in optimization | `0.0` | MW | ASSUMPTION | Brownfield mapping choice | Assumption |
| Technology cost assumptions | `pv_capex_eur_per_wacmax_2030` | PV CAPEX input | `0.69` | EUR/W | Danish Energy Agency (ENS), *Technology Data Catalogue for el and DH - 0017* (catalogue portal: <https://ens.dk/en/analyses-and-statistics/technology-catalogues>) | Converted to EUR/MW by multiplying by `1e6` | Source-based |
| Technology cost assumptions | `pv_fom_eur_per_mw_year` | PV fixed O&M | `8,800` | EUR/(MW·yr) | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Technology cost assumptions | `pv_life_years` | PV lifetime | `40` | years | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Technology cost assumptions | `wind_capex_meur_per_mw_2030` | Wind CAPEX input | `0.91` | MEUR/MW | ENS, *Technology Data Catalogue for el and DH - 0017* (incl. grid connection case used in project) | Converted to EUR/MW by multiplying by `1e6` | Source-based |
| Technology cost assumptions | `wind_fom_eur_per_mw_year` | Wind fixed O&M | `22,300` | EUR/(MW·yr) | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Technology cost assumptions | `wind_life_years` | Wind lifetime | `30` | years | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Technology cost assumptions | `ccgt_capex_meur_per_mw_2030` | CCGT CAPEX input | `0.83` | MEUR/MW | ENS, *Technology Data Catalogue for el and DH - 0017* | Converted to EUR/MW by multiplying by `1e6` | Source-based |
| Technology cost assumptions | `ccgt_fom_eur_per_mw_year` | CCGT fixed O&M | `27,800` | EUR/(MW·yr) | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Technology cost assumptions | `ccgt_vom_eur_per_mwh` | CCGT variable O&M | `4.2` | EUR/MWh | ENS catalogue family / project extraction from *Technology Data Catalogue for el and DH - 0017* | Direct input | Documented |
| Technology cost assumptions | `ccgt_eta_el` | CCGT electrical efficiency | `0.50` | - | ENS catalogue family / project extraction from *Technology Data Catalogue for el and DH - 0017* | Direct input | Documented |
| Technology cost assumptions | `ccgt_life_years` | CCGT lifetime | `25` | years | ENS, *Technology Data Catalogue for el and DH - 0017* | Direct input | Source-based |
| Battery assumptions | `bat_life_years` | Battery economic lifetime | `20` | years | Mixed: project assumption aligned to ENS storage-catalogue structure (*Teknologikatalog for Energilagring – 0010*) | Used in annualisation of power and energy CAPEX | Partially documented |
| Battery assumptions | `bat_capex_power_meur_per_mw_2030` | Battery power CAPEX | `0.108` | MEUR/MW | Mixed: project history + ENS storage catalogue family (*Teknologikatalog for Energilagring – 0010*) | Converted to EUR/MW by multiplying by `1e6` | Needs reconciliation |
| Battery assumptions | `bat_capex_energy_meur_per_mwh_2030` | Battery energy CAPEX | `0.084` | MEUR/MWh | Mixed: project history + ENS storage catalogue family (*Teknologikatalog for Energilagring – 0010*) | Converted to EUR/MWh by multiplying by `1e6` | Needs reconciliation |
| Battery assumptions | `bat_fom_eur_per_mw_year` | Battery fixed O&M | `8,091` | EUR/(MW·yr) | Mixed: project history + ENS storage catalogue family (*Teknologikatalog for Energilagring – 0010*) | Added to annualised power CAPEX term | Needs reconciliation |
| Battery assumptions | `bat_eta_ch` | Battery charge efficiency | `0.98` | - | ASSUMPTION | Applied uniformly to all durations | Assumption |
| Battery assumptions | `bat_eta_dis` | Battery discharge efficiency | `0.97` | - | ASSUMPTION | Applied uniformly to all durations | Assumption |
| Thermal operating assumptions | `boe_btu` | Energy content of one BOE | `5.8e6` | BTU/boe | BP Statistical Review 2022, Approximate conversion factors (<https://www.bp.com/content/dam/bp/business-sites/en/global/corporate/pdfs/energy-economics/statistical-review/bp-stats-review-2022-approximate-conversion-factors.pdf>) | Converted to MWh_th via `boe_to_mwh_th` | Documented |
| Thermal operating assumptions | `oil_price_eur_per_boe_2030` | Oil fuel price assumption | `72.2` | EUR/boe | SOURCE NEEDED | Used in `fuel_cost_eur_per_mwh_e` | Needs source verification |
| Thermal operating assumptions | `gas_price_eur_per_boe_2030` | Gas fuel price assumption | `36.2` | EUR/boe | SOURCE NEEDED | Used in `fuel_cost_eur_per_mwh_e` | Needs source verification |
| Thermal operating assumptions | `eta_oil_el` | Oil plant electrical efficiency | `0.37` | - | ASSUMPTION | Used in variable cost + emissions calculations | Assumption |
| Thermal operating assumptions | `vom_oil_eur_per_mwh` | Oil variable O&M | `6.740641678956848` | EUR/MWh | ASSUMPTION | Added to oil fuel cost | Assumption |
| Thermal operating assumptions | `ef_oil_kg_per_gj_th` | Oil emission factor | `72.81306265404072` | kgCO2/GJ_th | ASSUMPTION | Used in `emissions_tco2_per_mwh_e` | Assumption |
| Thermal operating assumptions | `ef_gas_kg_per_gj_th` | Gas emission factor | `52.924528301886795` | kgCO2/GJ_th | ASSUMPTION | Used in `emissions_tco2_per_mwh_e` | Assumption |
| Reliability / reserve assumptions | `sync_min_frac` | Minimum synchronous generation share | `0.20` | fraction of served demand | ASSUMPTION | Enforced in model constraints | Assumption |
| Reliability / reserve assumptions | `reserve_frac` | Reserve requirement fraction | `0.10` | fraction of demand | ASSUMPTION | Enforced in reserve-headroom constraint | Assumption |
| Thermal flexibility assumptions | `ramp_oil_mw_per_h` | Oil ramp-rate limit | `300` | MW/h | ASSUMPTION | Enforced between consecutive hours | Assumption |
| Thermal flexibility assumptions | `ramp_gas_mw_per_h` | Gas ramp-rate limit | `300` | MW/h | ASSUMPTION | Enforced between consecutive hours | Assumption |
| Penalty assumptions | `curt_penalty` | Curtailment penalty in objective | `5.0` | EUR/MWh curtailed | ASSUMPTION | Multiplied by curtailed energy in objective | Assumption |
| Penalty assumptions | `reserve_slack_penalty` | Reserve shortfall penalty in objective | `1.0e6` | EUR/MWh shortfall-equivalent | ASSUMPTION | Multiplied by reserve slack variable | Assumption |
| Policy assumptions | `oil_factor` | Available share of base oil fleet per scenario | scenario-dependent (`0` to `1`) | fraction | ASSUMPTION | `cap_exist_oil = oil_factor * cap_exist_oil_base` | Assumption |
| Policy assumptions | `voll` | Value of lost load | scenario-dependent | EUR/MWh | Mixed: baseline literature (`6500`), plus ASSUMPTION sensitivity values (`2000`, `10000`) | Passed directly from default or sweep grid |  Documented |
| Policy assumptions | `carbon_tax` | Carbon tax level | scenario-dependent | EUR/tCO2 | ASSUMPTION | Passed directly from default or sweep grid | Assumption |
| Derived quantities | `capex_pv`, `capex_wind`, `capex_gas` | Annualised investment costs | runtime-derived | EUR/(MW·yr) | DERIVED | `annualise_mw_year(capex, fom, r, n)` | Derived (validated) |
| Derived quantities | `capex_bat_P`, `capex_bat_E` | Annualised battery power/energy costs by duration | runtime-derived | EUR/(MW·yr), EUR/(MWh·yr) | DERIVED | `annualise_mw_year` and `annualise_mwh_year`; duplicated across durations | Derived |
| Derived quantities | `cvar_oil`, `cvar_gas` | Fuel + VOM variable generation cost | runtime-derived | EUR/MWh_e | DERIVED | `price/boe_mwh_th/eta + vom` | Derived |
| Derived quantities | `e_oil`, `e_gas` | Emissions intensity | runtime-derived | tCO2/MWh_e | DERIVED | `ef_kg_per_gj_th * 3.6 / (1000*eta)` | Derived |
## 4. Time-series and input data audit
| Dataset / file | Description | Used in | Source | Time coverage | Processing steps | Status | Notes |
|---|---|---|---|---|---|---|---|
| `data/timeseries_2019_2030_scaled.csv` | Primary model input with timestamp, demand, PV CF, wind CF | `run_base.jl` and `run_sensitivity.jl` via `io.jl::load_timeseries` | DERIVED by `build_timeseries_2019_2030_scaled.py` from demand workbook + Renewables.ninja PV/wind CSVs; 2030 peak target from TSOC annual report | 2019 hourly sequence (`8760` rows expected) | Demand: 15-min to hourly average, DST gap interpolation, then scale to 2030 peak (1583 MW). PV/wind: parse Ninja UTC timestamps, convert to local time, align to demand index, interpolate edge gaps | Documented | Current default input path in `params.jl`; this file is a preprocessing output, not a primary source. |
| `data/Ημερήσια Παραγωγή Ηλεκτρικού Συστήματος - 2019.xlsx.xls` | Raw demand/generation workbook used to construct hourly demand series | `build_timeseries_2019_2030_scaled.py` | Cyprus TSO archive: <https://tsoc.org.cy/electrical-system/archive-total-daily-system-generation-on-the-transmission-system/> | 2019 (15-min raw, converted to hourly) | Reads sheet `2019`, selects total-system-generation column, groups to hourly mean, fills missing local hour by interpolation | Documented | File naming/local copy timestamp should be tracked with checksum for strict reproducibility. |
| `data/ninja_pv_34.8824_33.3914_corrected.csv` | PV hourly output/CF proxy series | `build_timeseries_2019_2030_scaled.py` | Renewables.ninja Point API: <https://www.renewables.ninja> (header shows API metadata + DOI `10.1016/j.energy.2016.08.060`) | 2019-01-01 to 2019-12-31 hourly (time in UTC; local_time Europe/Athens in source file) | Metadata rows skipped; parse `time` as UTC; convert to local model clock; average duplicate local timestamps; reindex to demand index; interpolate remaining gaps | Partially documented | Header metadata recovered: `lat=34.882424490120535`, `lon=33.39135523945498`, `dataset=merra2`, `capacity=1`, `system_loss=0.1`, `tracking=0`, `tilt=35`, `azim=180`, `raw=true`. |
| `data/ninja_wind_34.8824_33.3914_corrected.csv` | Wind hourly output/CF proxy series | `build_timeseries_2019_2030_scaled.py` | Renewables.ninja Point API: <https://www.renewables.ninja> (header shows API metadata + DOI `10.1016/j.energy.2016.08.068`) | 2019-01-01 to 2019-12-31 hourly (time in UTC; local_time Europe/Athens in source file) | Same pipeline as PV: UTC parse, local conversion, duplicate handling, reindex, interpolation | Partially documented | Header metadata recovered: `lat=34.882424490120535`, `lon=33.39135523945498`, `dataset=merra2`, `capacity=1`, `height=80`, `turbine=Vestas V90 2000`, `raw=true`. |
| `build_timeseries_2019_2030_scaled.py` | Preprocessing script that creates the default model input CSV | External preprocessing stage feeding model input | Repository-authored script | Operates on 2019 source files | Demand scaling to 2030 peak target; UTC/local alignment for RE CF; consistency checks; CSV export | Documented in code | Not called automatically by Julia runners. |

## 5. Derived quantities and transformations
- **CAPEX annualisation**
  - What is transformed: one-time CAPEX (+ FOM for power assets) into annualized cost terms.
  - Where it happens: `params.jl` in `crf`, `annualise_mw_year`, `annualise_mwh_year`, used in `build_params`.
  - Assumptions: discount rate, technology lifetime, FOM values, and CAPEX units are correct.

- **Validated annualisation reproductions (r = 4%)**
  - What is transformed: ENS-catalogue 2030 CAPEX/FOM/lifetime assumptions to annualised values.
  - Where it happens: `params.jl::annualise_mw_year` and `crf`.
  - Assumptions: CAPEX/FOM/lifetime triplets correspond to the selected ENS technology-catalogue cases.
  - Check formulas:
    - `PV = 690000 * CRF(0.04,40) + 8800 = 43661.21 EUR/(MW*yr)`
    - `Wind = 910000 * CRF(0.04,30) + 22300 = 74925.39 EUR/(MW*yr)`
    - `Gas = 830000 * CRF(0.04,25) + 27800 = 80929.93 EUR/(MW*yr)`

- **Demand scaling to planning-year peak**
  - What is transformed: 2019 hourly demand profile to a 2030 profile preserving shape.
  - Where it happens: `build_timeseries_2019_2030_scaled.py` (`scale_factor = TARGET_2030_PEAK_MW / peak_2019`).
  - Assumptions: scalar scaling is appropriate; target 2030 peak (`1583 MW`) is taken from `TSOC_Annual_Report_2023.pdf` available via <https://tsoc.org.cy/organization/annual-reports/> (exact page/table reference still to be recorded).

- **UTC-to-local renewable alignment**
  - What is transformed: PV/wind hourly timestamps from UTC to `Europe/Nicosia` local time.
  - Where it happens: `build_timeseries_2019_2030_scaled.py::read_ninja_cf`.
  - Assumptions: source timestamps are UTC; duplicate/missing local timestamps can be averaged/interpolated.

- **Missing-value interpolation/fill**
  - What is transformed: gaps in demand or CF series after reindexing.
  - Where it happens: preprocessing script (`interpolate` + `ffill`/`bfill`) and `io.jl` neighbor-fill for input CF columns.
  - Assumptions: local interpolation does not materially bias system-level results.

- **Fuel-cost construction**
  - What is transformed: fuel price per BOE into electrical variable cost per MWh.
  - Where it happens: `params.jl::fuel_cost_eur_per_mwh_e` with `boe_to_mwh_th` conversion.
  - Assumptions: BOE thermal content, efficiencies, and VOM values are accurate.

- **Emissions-intensity construction**
  - What is transformed: thermal emission factors in kg/GJ_th into tCO2/MWh_e.
  - Where it happens: `params.jl::emissions_tco2_per_mwh_e`.
  - Assumptions: emission factors and plant efficiencies are representative.

- **Capacity-factor to generation-limit mapping**
  - What is transformed: hourly CF values into maximum dispatch/curtailment envelope.
  - Where it happens: `model.jl` constraints `p_pv + curt_pv == pv_cf * cap_pv` and equivalent wind equation.
  - Assumptions: CF values are preprocessed correctly and represent deliverable availability.

- **Battery power/energy coupling and aggregation**
  - What is transformed: independent battery investment variables into duration-locked assets and aggregated dispatch terms.
  - Where it happens: `model.jl` (`Ebat[h] == h * Pbat[h]`, SOC equations, charge/discharge totals) and `outputs.jl` aggregations.
  - Assumptions: duration classes share identical efficiencies and cost rates.

- **Scenario-parameter overrides**
  - What is transformed: baseline parameter set into scenario-specific variants.
  - Where it happens: `run_sensitivity.jl` loops over (`oil_factor`, `voll`, `carbon_tax`) and passes to `build_params`.
  - Assumptions: scenario axes and ranges are policy-relevant and sufficient for analysis goals.

## 6. Assumptions requiring verification
- Exact in-repository citation pointers (specific ENS PDF/file/sheet/cell) for each CAPEX/FOM/lifetime input used in `params.jl`.
- Exact in-paper locator (page/table/section) for the `6500 EUR/MWh` VoLL value used as baseline.
- Source and rationale for fuel prices (`oil_price_eur_per_boe_2030`, `gas_price_eur_per_boe_2030`).
- Verification of thermal emission factors and oil efficiency values currently marked provisional assumptions.
- Documentation for operational constraints and penalties (`sync_min_frac`, `reserve_frac`, ramps, curtailment penalty, reserve slack penalty).
- Full provenance for the `*_corrected.csv` modifications (who changed what relative to raw Renewables.ninja exports, and when).
- Reconciliation note for battery CAPEX/FOM pathway: uploaded workbook supports structure but does not exactly reproduce the historical annualised project pair.
