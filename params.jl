using Printf

# Sensitivity axes used by this model runner.
const BATTERY_DURATIONS = Int[2, 4, 8]
const OIL_FACTOR_LEVELS = collect(0.0:0.05:0.30)
# Keep these explicit in code so scenario sweeps are transparent in version control.
const VOLL_GRID = [2000.0, 6500.0, 10000.0]
const CARBON_TAX_GRID = collect(0.0:10.0:50.0)

# Base run defaults.
const DEFAULT_OIL_FACTOR = 0.30
const DEFAULT_VOLL = 6500.0
const DEFAULT_CARBON_TAX = 30.0

# Default input path used by both base and sensitivity runs.
const DEFAULT_TIMESERIES_RELATIVE = joinpath("data", "timeseries_2019_2030_scaled.csv")

# Core financial / unit constants.
const DISCOUNT_RATE = 0.04
const BTU_TO_KWH = 0.00029307107

# =============================================================================
# Parameter + Variable Reference Index (single in-code source of traceability)
# =============================================================================
#
# Parameter provenance summary (key fields from sourced_inputs()):
# - discount_rate: EC SWD(2021)429 social discount rate.
# - voll default and grid: literature value 6.50 EUR/kWh (=6500 EUR/MWh) and
#   policy sweep values [2000, 6500, 10000] EUR/MWh.
# - carbon tax default/grid: policy scenario values [0, 10, 20, 30, 40, 50]
#   EUR/tCO2 with 30 EUR/tCO2 as default run point.
# - Existing capacities:
#   - cap_exist_pv from PV component totals
#   - cap_exist_wind from installed wind
#   - cap_exist_oil_base from installed oil
#   - cap_exist_gas set by brownfield thermal mapping choice in this model.
# - Technology CAPEX/FOM/lifetimes:
#   - PV, wind, CCGT from technology catalogue values
#   - battery power/energy/fixed O&M from storage workbook values.
# - Fuel/emissions:
#   - BOE and BTU conversion constants
#   - oil/gas prices per boe
#   - eta_oil_el, vom_oil_eur_per_mwh, ef_oil_kg_per_gj_th,
#     ef_gas_kg_per_gj_th are explicit assumptions (TODO replace with final
#     sourced thermal performance/emissions factors).
# - Operational/security assumptions:
#   - sync_min_frac, reserve_frac, ramp_oil_mw_per_h, ramp_gas_mw_per_h,
#     curt_penalty, reserve_slack_penalty.
#
# Model variable index (defined in model.jl):
# - Investment variables:
#   dcap_pv, dcap_wind, dcap_gas, Pbat[h], Ebat[h]
# - Dispatch variables:
#   p_pv[t], p_wind[t], curt_pv[t], curt_wind[t], p_oil[t], p_gas[t]
# - Storage time-coupled variables:
#   charge[h,t], discharge[h,t], soc[h,t]
# - Reliability/security slack variables:
#   nse[t], reserve_shortfall[t]
#
struct ModelParams
    cap_exist_pv::Float64
    cap_exist_wind::Float64
    cap_exist_oil_base::Float64
    cap_exist_oil::Float64
    cap_exist_gas::Float64
    capex_pv::Float64
    capex_wind::Float64
    capex_gas::Float64
    capex_bat_P::Dict{Int,Float64}
    capex_bat_E::Dict{Int,Float64}
    cvar_oil::Float64
    cvar_gas::Float64
    e_oil::Float64
    e_gas::Float64
    eta_ch::Dict{Int,Float64}
    eta_dis::Dict{Int,Float64}
    voll::Float64
    carbon_tax::Float64
    oil_factor::Float64
    sync_min_frac::Float64
    reserve_frac::Float64
    ramp_oil_mw_per_h::Float64
    ramp_gas_mw_per_h::Float64
    curt_penalty::Float64
    reserve_slack_penalty::Float64
end

# Numeric inputs and assumptions used by this model run configuration.
function sourced_inputs()
    return (
        pv_commercial_mw = 358.4,
        pv_self_consumption_excl_metering_mw = 59.24,
        pv_own_use_mw = 2.08,
        pv_net_metering_mw = 239.8,
        cap_exist_wind_mw = 157.5,
        cap_exist_oil_mw = 1482.5,
        # Model mapping choice for the brownfield thermal baseline:
        # represent existing thermal fleet as oil-only in optimisation.
        cap_exist_gas_mw = 0.0,
        # Reference table value from CERA/CEER report (not used directly in this mapping).
        cap_exist_gas_table4_mw = 440.0,

        pv_capex_eur_per_wacmax_2030 = 0.69,
        pv_fom_eur_per_mw_year = 8_800.0,
        pv_life_years = 40,

        wind_capex_meur_per_mw_2030 = 0.91,
        wind_fom_eur_per_mw_year = 22_300.0,
        wind_life_years = 30,

        ccgt_capex_meur_per_mw_2030 = 0.83,
        ccgt_fom_eur_per_mw_year = 27_800.0,
        ccgt_vom_eur_per_mwh = 4.2,
        ccgt_eta_el = 0.50,
        ccgt_life_years = 25,

        boe_btu = 5.8e6,
        btu_to_kwh = BTU_TO_KWH,
        oil_price_eur_per_boe_2030 = 72.2,
        gas_price_eur_per_boe_2030 = 36.2,

        # Thermal/oil factors below are currently modelling assumptions
        # (replace with sourced IPCC/ETS MRV factors when finalising).
        eta_oil_el = 0.37,
        vom_oil_eur_per_mwh = 6.740641678956848,
        ef_oil_kg_per_gj_th = 72.81306265404072,
        ef_gas_kg_per_gj_th = 52.924528301886795,

        bat_life_years = 20,
        bat_capex_power_meur_per_mw_2030 = 0.108,
        bat_capex_energy_meur_per_mwh_2030 = 0.084,
        bat_fom_eur_per_mw_year = 8_091.0,
        bat_eta_ch = 0.98,
        bat_eta_dis = 0.97,

        # Assumption block used by this model:
        # - sync_min_frac: minimum synchronous generation share requirement.
        # - reserve_frac: spinning/headroom reserve requirement share.
        # - ramp_*: hourly ramp-rate limits for thermal units.
        # - curt_penalty: soft economic penalty on renewable curtailment.
        # - reserve_slack_penalty: large penalty to strongly discourage
        #   reserve shortfall slack in otherwise feasible cases.
        sync_min_frac = 0.20,
        reserve_frac = 0.10,
        ramp_oil_mw_per_h = 300.0,
        ramp_gas_mw_per_h = 300.0,
        curt_penalty = 5.0,
        reserve_slack_penalty = 1.0e6,
        discount_rate = DISCOUNT_RATE,
    )
end

crf(r::Real, n::Real) = r / (1.0 - (1.0 + r)^(-n))

annualise_mw_year(capex_eur_per_mw::Real, fom_eur_per_mw_year::Real, r::Real, n::Real) =
    capex_eur_per_mw * crf(r, n) + fom_eur_per_mw_year

annualise_mwh_year(capex_eur_per_mwh::Real, r::Real, n::Real) =
    capex_eur_per_mwh * crf(r, n)

boe_to_mwh_th(boe_btu::Real; btu_to_kwh::Real=BTU_TO_KWH) = boe_btu * btu_to_kwh / 1000.0

fuel_cost_eur_per_mwh_e(price_eur_per_boe::Real, boe_mwh_th::Real, eta_el::Real, vom_eur_per_mwh::Real) =
    price_eur_per_boe / boe_mwh_th / eta_el + vom_eur_per_mwh

emissions_tco2_per_mwh_e(ef_kg_per_gj_th::Real, eta_el::Real) = ef_kg_per_gj_th * 3.6 / (1000.0 * eta_el)

function build_params(; oil_factor::Float64=DEFAULT_OIL_FACTOR, voll::Float64=DEFAULT_VOLL, carbon_tax::Float64=DEFAULT_CARBON_TAX)
    if !(0.0 <= oil_factor <= 1.0)
        error("oil_factor must be in [0, 1]. Got $oil_factor")
    end
    if voll < 0.0
        error("voll must be >= 0. Got $voll")
    end
    if carbon_tax < 0.0
        error("carbon_tax must be >= 0. Got $carbon_tax")
    end

    s = sourced_inputs()
    r = s.discount_rate

    pv_capex_eur_per_mw = s.pv_capex_eur_per_wacmax_2030 * 1.0e6
    wind_capex_eur_per_mw = s.wind_capex_meur_per_mw_2030 * 1.0e6
    ccgt_capex_eur_per_mw = s.ccgt_capex_meur_per_mw_2030 * 1.0e6
    bat_capex_power_eur_per_mw = s.bat_capex_power_meur_per_mw_2030 * 1.0e6
    bat_capex_energy_eur_per_mwh = s.bat_capex_energy_meur_per_mwh_2030 * 1.0e6

    cap_exist_pv =
        s.pv_commercial_mw +
        s.pv_self_consumption_excl_metering_mw +
        s.pv_own_use_mw +
        s.pv_net_metering_mw

    capex_pv = annualise_mw_year(pv_capex_eur_per_mw, s.pv_fom_eur_per_mw_year, r, s.pv_life_years)
    capex_wind = annualise_mw_year(wind_capex_eur_per_mw, s.wind_fom_eur_per_mw_year, r, s.wind_life_years)
    capex_gas = annualise_mw_year(ccgt_capex_eur_per_mw, s.ccgt_fom_eur_per_mw_year, r, s.ccgt_life_years)

    capex_bat_P_scalar = annualise_mw_year(bat_capex_power_eur_per_mw, s.bat_fom_eur_per_mw_year, r, s.bat_life_years)
    capex_bat_E_scalar = annualise_mwh_year(bat_capex_energy_eur_per_mwh, r, s.bat_life_years)

    capex_bat_P = Dict(h => capex_bat_P_scalar for h in BATTERY_DURATIONS)
    capex_bat_E = Dict(h => capex_bat_E_scalar for h in BATTERY_DURATIONS)
    eta_ch = Dict(h => s.bat_eta_ch for h in BATTERY_DURATIONS)
    eta_dis = Dict(h => s.bat_eta_dis for h in BATTERY_DURATIONS)

    boe_mwh_th = boe_to_mwh_th(s.boe_btu; btu_to_kwh=s.btu_to_kwh)
    cvar_gas = fuel_cost_eur_per_mwh_e(s.gas_price_eur_per_boe_2030, boe_mwh_th, s.ccgt_eta_el, s.ccgt_vom_eur_per_mwh)
    cvar_oil = fuel_cost_eur_per_mwh_e(s.oil_price_eur_per_boe_2030, boe_mwh_th, s.eta_oil_el, s.vom_oil_eur_per_mwh)

    e_gas = emissions_tco2_per_mwh_e(s.ef_gas_kg_per_gj_th, s.ccgt_eta_el)
    e_oil = emissions_tco2_per_mwh_e(s.ef_oil_kg_per_gj_th, s.eta_oil_el)

    cap_exist_oil_base = s.cap_exist_oil_mw
    cap_exist_oil = oil_factor * cap_exist_oil_base

    return ModelParams(
        cap_exist_pv,
        s.cap_exist_wind_mw,
        cap_exist_oil_base,
        cap_exist_oil,
        s.cap_exist_gas_mw,
        capex_pv,
        capex_wind,
        capex_gas,
        capex_bat_P,
        capex_bat_E,
        cvar_oil,
        cvar_gas,
        e_oil,
        e_gas,
        eta_ch,
        eta_dis,
        voll,
        carbon_tax,
        oil_factor,
        s.sync_min_frac,
        s.reserve_frac,
        s.ramp_oil_mw_per_h,
        s.ramp_gas_mw_per_h,
        s.curt_penalty,
        s.reserve_slack_penalty,
    )
end

function _format_integer_if_possible(x::Real)
    xf = Float64(x)
    if isapprox(xf, round(xf); atol=1e-9)
        return string(Int(round(xf)))
    end
    txt = @sprintf("%.2f", xf)
    return replace(replace(txt, r"0+$" => ""), r"\.$" => "")
end

function make_scenario_name(oil_factor::Real, voll::Real, carbon_tax::Real)
    oil_txt = @sprintf("%.2f", Float64(oil_factor))
    return "base_oil$(oil_txt)_voll$(_format_integer_if_possible(voll))_co2$(_format_integer_if_possible(carbon_tax))"
end

function project_root()
    # This model package is self-contained, so its root is this directory.
    return normpath(@__DIR__)
end

function resolve_timeseries_path(cli_arg::Union{Nothing,String})
    if cli_arg !== nothing
        return isabspath(cli_arg) ? cli_arg : normpath(joinpath(pwd(), cli_arg))
    end

    # Primary expected location.
    default_path = joinpath(project_root(), DEFAULT_TIMESERIES_RELATIVE)
    if isfile(default_path)
        return default_path
    end

    # If the default file name is not present, choose a CSV from ./data.
    # This keeps the runner robust across repositories that use different
    # timeseries file names while still remaining self-contained.
    data_dir = joinpath(project_root(), "data")
    if isdir(data_dir)
        files = filter(f -> endswith(lowercase(f), ".csv"), readdir(data_dir))
        if !isempty(files)
            # Prefer names that look like final planning inputs (2030/scaled),
            # then fall back to alphabetical order.
            sort!(files, by = f -> (
                occursin("2030", lowercase(f)) ? 0 : 1,
                occursin("scaled", lowercase(f)) ? 0 : 1,
                lowercase(f),
            ))
            return joinpath(data_dir, first(files))
        end
    end

    return default_path
end

expected_sensitivity_rows() = length(OIL_FACTOR_LEVELS) * length(VOLL_GRID) * length(CARBON_TAX_GRID)

format_grid(values::Vector{Float64}) = join([_format_integer_if_possible(v) for v in values], ", ")
