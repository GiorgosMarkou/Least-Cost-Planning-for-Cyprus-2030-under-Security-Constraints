using JuMP
using HiGHS
using DataFrames
import MathOptInterface as MOI

# --------------------------------------------------------------------------
# Construct the capacity-expansion + hourly dispatch model.
# Inputs:
# - df: normalized hourly timeseries from io.jl
# - params: scenario-specific parameter bundle from params.jl
# - H: battery duration classes (hours), typically [2, 4, 8]
# Returns a bundle of:
# - model: JuMP optimization model
# - vars: references to decision variables
# - expr: references to useful objective components/expressions
# - data: cached input arrays used for post-processing
# --------------------------------------------------------------------------
function build_model(df::DataFrame, params::ModelParams, H::Vector{Int}=BATTERY_DURATIONS)
    # Convert DataFrame columns to typed vectors once to avoid repeated dynamic access.
    T = collect(1:nrow(df))
    demand = Vector{Float64}(df.demand_mwh)
    pv_cf = Vector{Float64}(df.pv_cf)
    wind_cf = Vector{Float64}(df.wind_cf)
    weight = Vector{Float64}(df.weight)

    model = Model(HiGHS.Optimizer)
    set_silent(model)

    # Investment decisions (annualized costs applied in objective).
    @variable(model, dcap_pv >= 0)
    @variable(model, dcap_wind >= 0)
    @variable(model, dcap_gas >= 0)
    @variable(model, Pbat[h in H] >= 0)
    @variable(model, Ebat[h in H] >= 0)

    # Hourly production/curtailment/reliability variables.
    @variable(model, p_pv[t in T] >= 0)
    @variable(model, p_wind[t in T] >= 0)
    @variable(model, curt_pv[t in T] >= 0)
    @variable(model, curt_wind[t in T] >= 0)
    @variable(model, p_oil[t in T] >= 0)
    @variable(model, p_gas[t in T] >= 0)
    @variable(model, reserve_shortfall[t in T] >= 0)
    @variable(model, nse[t in T] >= 0)

    @variable(model, charge[h in H, t in T] >= 0)
    @variable(model, discharge[h in H, t in T] >= 0)
    @variable(model, soc[h in H, t in T] >= 0)

    # Installed capacities after investment additions.
    @expression(model, cap_pv, params.cap_exist_pv + dcap_pv)
    @expression(model, cap_wind, params.cap_exist_wind + dcap_wind)
    @expression(model, cap_gas, params.cap_exist_gas + dcap_gas)
    cap_oil = params.cap_exist_oil

    # Energy balance each hour:
    # generation + net battery discharge + non-served energy = demand.
    @constraint(model, [t in T],
        p_pv[t] + p_wind[t] + p_oil[t] + p_gas[t] +
        sum(discharge[h, t] for h in H) - sum(charge[h, t] for h in H) + nse[t] == demand[t]
    )

    # Renewable potential split into delivered energy and curtailment.
    @constraint(model, [t in T], p_pv[t] + curt_pv[t] == pv_cf[t] * cap_pv)
    @constraint(model, [t in T], p_wind[t] + curt_wind[t] == wind_cf[t] * cap_wind)

    # Thermal dispatch cannot exceed available capacity.
    @constraint(model, [t in T], p_oil[t] <= cap_oil)
    @constraint(model, [t in T], p_gas[t] <= cap_gas)

    # Minimum synchronous generation proxy, tied to served demand.
    @constraint(model, [t in T], p_oil[t] + p_gas[t] >= params.sync_min_frac * (demand[t] - nse[t]))

    # Reserve adequacy: thermal headroom + battery upward headroom + slack.
    @constraint(model, [t in T],
        (cap_oil - p_oil[t]) +
        (cap_gas - p_gas[t]) +
        sum(Pbat[h] - discharge[h, t] for h in H) +
        reserve_shortfall[t] >= params.reserve_frac * demand[t]
    )

    # Battery operating bounds.
    @constraint(model, [h in H, t in T], charge[h, t] <= Pbat[h])
    @constraint(model, [h in H, t in T], discharge[h, t] <= Pbat[h])
    @constraint(model, [h in H, t in T], soc[h, t] <= Ebat[h])

    # Enforce fixed duration classes: E = h * P.
    @constraint(model, [h in H], Ebat[h] == h * Pbat[h])

    t_last = last(T)
    # Cyclic state-of-charge (end-of-year links back to first hour).
    @constraint(model, [h in H],
        soc[h, 1] == soc[h, t_last] + params.eta_ch[h] * charge[h, 1] - (1.0 / params.eta_dis[h]) * discharge[h, 1]
    )

    if length(T) > 1
        # Standard forward SOC dynamics for all subsequent hours.
        @constraint(model, [h in H, t in T[2:end]],
            soc[h, t] == soc[h, t - 1] + params.eta_ch[h] * charge[h, t] - (1.0 / params.eta_dis[h]) * discharge[h, t]
        )
        # Symmetric ramp limits for thermal technologies.
        @constraint(model, [t in T[2:end]], p_oil[t] - p_oil[t - 1] <= params.ramp_oil_mw_per_h)
        @constraint(model, [t in T[2:end]], p_oil[t - 1] - p_oil[t] <= params.ramp_oil_mw_per_h)
        @constraint(model, [t in T[2:end]], p_gas[t] - p_gas[t - 1] <= params.ramp_gas_mw_per_h)
        @constraint(model, [t in T[2:end]], p_gas[t - 1] - p_gas[t] <= params.ramp_gas_mw_per_h)
    end

    # Investment cost block (annualized EUR/year).
    investment_cost = @expression(model,
        params.capex_pv * dcap_pv +
        params.capex_wind * dcap_wind +
        params.capex_gas * dcap_gas +
        sum(params.capex_bat_P[h] * Pbat[h] + params.capex_bat_E[h] * Ebat[h] for h in H)
    )

    # Operating-cost components retained as separate expressions for transparent reporting.
    oil_cost_total = @expression(model, sum(weight[t] * params.cvar_oil * p_oil[t] for t in T))
    gas_cost_total = @expression(model, sum(weight[t] * params.cvar_gas * p_gas[t] for t in T))
    carbon_cost_component = @expression(model,
        sum(weight[t] * params.carbon_tax * (params.e_oil * p_oil[t] + params.e_gas * p_gas[t]) for t in T)
    )
    voll_cost_component = @expression(model, sum(weight[t] * params.voll * nse[t] for t in T))
    curtailment_penalty_component = @expression(model,
        sum(weight[t] * params.curt_penalty * (curt_pv[t] + curt_wind[t]) for t in T)
    )
    reserve_shortfall_penalty_component = @expression(model,
        sum(weight[t] * params.reserve_slack_penalty * reserve_shortfall[t] for t in T)
    )

    # Total operating cost (energy + policy + penalty terms).
    operating_cost = @expression(model,
        oil_cost_total + gas_cost_total + carbon_cost_component +
        voll_cost_component + curtailment_penalty_component + reserve_shortfall_penalty_component
    )

    # Objective: minimum total annual system cost.
    @objective(model, Min, investment_cost + operating_cost)

    # Return named references to avoid brittle index-based post-processing.
    vars = (
        dcap_pv = dcap_pv,
        dcap_wind = dcap_wind,
        dcap_gas = dcap_gas,
        Pbat = Pbat,
        Ebat = Ebat,
        p_pv = p_pv,
        p_wind = p_wind,
        curt_pv = curt_pv,
        curt_wind = curt_wind,
        p_oil = p_oil,
        p_gas = p_gas,
        charge = charge,
        discharge = discharge,
        soc = soc,
        reserve_shortfall = reserve_shortfall,
        nse = nse,
    )

    expr = (
        cap_pv = cap_pv,
        cap_wind = cap_wind,
        cap_gas = cap_gas,
        investment_cost = investment_cost,
        operating_cost = operating_cost,
        oil_cost_total = oil_cost_total,
        gas_cost_total = gas_cost_total,
        carbon_cost_component = carbon_cost_component,
        voll_cost_component = voll_cost_component,
        curtailment_penalty_component = curtailment_penalty_component,
        reserve_shortfall_penalty_component = reserve_shortfall_penalty_component,
    )

    data = (
        T = T,
        H = H,
        demand = demand,
        pv_cf = pv_cf,
        wind_cf = wind_cf,
        weight = weight,
    )

    return (model = model, vars = vars, expr = expr, data = data)
end

# Solve and enforce strict optimality checks for reproducible reporting.
function solve_model!(model::Model)
    optimize!(model)
    term = termination_status(model)
    prim = primal_status(model)
    if term != MOI.OPTIMAL
        error("Solver did not terminate at OPTIMAL. termination_status=$(term), primal_status=$(prim)")
    end
    if prim != MOI.FEASIBLE_POINT
        error("Solver did not return FEASIBLE_POINT. termination_status=$(term), primal_status=$(prim)")
    end
    return (
        termination_status = string(term),
        primal_status = string(prim),
        objective_value = objective_value(model),
    )
end
