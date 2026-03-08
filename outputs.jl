using CSV
using DataFrames
using JuMP
using Printf

function build_summary_row(bundle, params::ModelParams; scenario_id::Int, scenario_name::String)
    model = bundle.model
    vars = bundle.vars
    expr = bundle.expr
    data = bundle.data

    T = data.T
    H = data.H
    demand = data.demand
    pv_cf = data.pv_cf
    wind_cf = data.wind_cf
    weight = data.weight

    dcap_pv = value(vars.dcap_pv)
    dcap_wind = value(vars.dcap_wind)
    dcap_gas = value(vars.dcap_gas)

    cap_pv = params.cap_exist_pv + dcap_pv
    cap_wind = params.cap_exist_wind + dcap_wind
    cap_oil = params.cap_exist_oil
    cap_gas = params.cap_exist_gas + dcap_gas

    # Pull hourly trajectories once, then aggregate all KPIs from these arrays.
    p_pv = [value(vars.p_pv[t]) for t in T]
    p_wind = [value(vars.p_wind[t]) for t in T]
    curt_pv = [value(vars.curt_pv[t]) for t in T]
    curt_wind = [value(vars.curt_wind[t]) for t in T]
    p_oil = [value(vars.p_oil[t]) for t in T]
    p_gas = [value(vars.p_gas[t]) for t in T]
    nse = [value(vars.nse[t]) for t in T]
    reserve_shortfall = [value(vars.reserve_shortfall[t]) for t in T]

    charge = Dict(h => [value(vars.charge[h, t]) for t in T] for h in H)
    discharge = Dict(h => [value(vars.discharge[h, t]) for t in T] for h in H)
    soc = Dict(h => [value(vars.soc[h, t]) for t in T] for h in H)

    Pbat = Dict(h => value(vars.Pbat[h]) for h in H)
    Ebat = Dict(h => value(vars.Ebat[h]) for h in H)

    # Demand and reliability summary.
    total_demand = sum(weight[t] * demand[t] for t in T)
    total_nse_mwh = sum(weight[t] * nse[t] for t in T)
    nse_pct = total_demand > 0 ? 100.0 * total_nse_mwh / total_demand : 0.0
    nse_hours = count(x -> x > 1e-6, nse)
    peak_nse = isempty(nse) ? 0.0 : maximum(nse)

    # Curtailment and renewable potential summary.
    pv_potential = [pv_cf[t] * cap_pv for t in T]
    wind_potential = [wind_cf[t] * cap_wind for t in T]
    total_curt_pv = sum(weight[t] * curt_pv[t] for t in T)
    total_curt_wind = sum(weight[t] * curt_wind[t] for t in T)
    total_curt = total_curt_pv + total_curt_wind
    total_renew_potential = sum(weight[t] * (pv_potential[t] + wind_potential[t]) for t in T)
    curt_pct_of_potential = total_renew_potential > 0 ? 100.0 * total_curt / total_renew_potential : 0.0

    # Security diagnostics derived from the same equations as the model constraints.
    reserve_headroom = [
        (cap_oil - p_oil[t]) +
        (cap_gas - p_gas[t]) +
        sum(Pbat[h] - discharge[h][t] for h in H) -
        params.reserve_frac * demand[t]
        for t in T
    ]
    must_run_slack = [p_oil[t] + p_gas[t] - params.sync_min_frac * (demand[t] - nse[t]) for t in T]

    total_reserve_shortfall = sum(weight[t] * reserve_shortfall[t] for t in T)
    reserve_shortfall_hours = count(x -> x > 1e-6, reserve_shortfall)
    max_reserve_shortfall = isempty(reserve_shortfall) ? 0.0 : maximum(reserve_shortfall)
    min_reserve_headroom = isempty(reserve_headroom) ? 0.0 : minimum(reserve_headroom)
    min_must_run_slack = isempty(must_run_slack) ? 0.0 : minimum(must_run_slack)

    # Objective breakdown components (read directly from JuMP expressions).
    investment_cost = value(expr.investment_cost)
    oil_cost_total = value(expr.oil_cost_total)
    gas_cost_total = value(expr.gas_cost_total)
    carbon_cost_component = value(expr.carbon_cost_component)
    voll_cost_component = value(expr.voll_cost_component)
    curtailment_penalty_component = value(expr.curtailment_penalty_component)
    reserve_shortfall_penalty_component = value(expr.reserve_shortfall_penalty_component)
    operating_cost = value(expr.operating_cost)

    total_generation_pv = sum(weight[t] * p_pv[t] for t in T)
    total_generation_wind = sum(weight[t] * p_wind[t] for t in T)
    total_generation_oil = sum(weight[t] * p_oil[t] for t in T)
    total_generation_gas = sum(weight[t] * p_gas[t] for t in T)
    total_battery_charge = sum(weight[t] * sum(charge[h][t] for h in H) for t in T)
    total_battery_discharge = sum(weight[t] * sum(discharge[h][t] for h in H) for t in T)

    Pbat_2 = get(Pbat, 2, 0.0)
    Ebat_2 = get(Ebat, 2, 0.0)
    Pbat_4 = get(Pbat, 4, 0.0)
    Ebat_4 = get(Ebat, 4, 0.0)
    Pbat_8 = get(Pbat, 8, 0.0)
    Ebat_8 = get(Ebat, 8, 0.0)

    # Single row schema used by both base and sensitivity outputs.
    return (
        scenario_id = scenario_id,
        scenario_name = scenario_name,
        oil_factor = params.oil_factor,
        voll = params.voll,
        carbon_tax = params.carbon_tax,

        termination_status = string(termination_status(model)),
        primal_status = string(primal_status(model)),

        objective_value = objective_value(model),
        investment_cost = investment_cost,
        operating_cost = operating_cost,
        oil_cost_total = oil_cost_total,
        gas_cost_total = gas_cost_total,
        carbon_cost_component = carbon_cost_component,
        voll_cost_component = voll_cost_component,
        curtailment_penalty_component = curtailment_penalty_component,
        reserve_shortfall_penalty_component = reserve_shortfall_penalty_component,

        total_demand = total_demand,
        total_nse_mwh = total_nse_mwh,
        nse_pct = nse_pct,
        nse_hours = nse_hours,
        peak_nse = peak_nse,

        total_curt_pv = total_curt_pv,
        total_curt_wind = total_curt_wind,
        total_curt = total_curt,
        curt_pct_of_potential = curt_pct_of_potential,

        total_reserve_shortfall = total_reserve_shortfall,
        reserve_shortfall_hours = reserve_shortfall_hours,
        max_reserve_shortfall = max_reserve_shortfall,
        min_reserve_headroom = min_reserve_headroom,
        min_must_run_slack = min_must_run_slack,

        cap_exist_pv = params.cap_exist_pv,
        cap_exist_wind = params.cap_exist_wind,
        cap_exist_oil_base = params.cap_exist_oil_base,
        cap_exist_oil = params.cap_exist_oil,
        cap_exist_gas = params.cap_exist_gas,
        cap_pv = cap_pv,
        cap_wind = cap_wind,
        cap_oil = cap_oil,
        cap_gas = cap_gas,
        dcap_pv = dcap_pv,
        dcap_wind = dcap_wind,
        dcap_gas = dcap_gas,

        Pbat_2 = Pbat_2,
        Ebat_2 = Ebat_2,
        Pbat_4 = Pbat_4,
        Ebat_4 = Ebat_4,
        Pbat_8 = Pbat_8,
        Ebat_8 = Ebat_8,
        Pbat_total = sum(values(Pbat)),
        Ebat_total = sum(values(Ebat)),

        total_generation_pv = total_generation_pv,
        total_generation_wind = total_generation_wind,
        total_generation_oil = total_generation_oil,
        total_generation_gas = total_generation_gas,
        total_battery_charge = total_battery_charge,
        total_battery_discharge = total_battery_discharge,

        sync_min_frac = params.sync_min_frac,
        reserve_frac = params.reserve_frac,
        ramp_oil_mw_per_h = params.ramp_oil_mw_per_h,
        ramp_gas_mw_per_h = params.ramp_gas_mw_per_h,
        curt_penalty = params.curt_penalty,
        reserve_slack_penalty = params.reserve_slack_penalty,
    )
end

function build_dispatch_table(input_df::DataFrame, bundle)
    vars = bundle.vars
    data = bundle.data
    T = data.T
    H = data.H

    # Dispatch export keeps raw technology detail plus convenience totals.
    charge_total = [sum(value(vars.charge[h, t]) for h in H) for t in T]
    discharge_total = [sum(value(vars.discharge[h, t]) for h in H) for t in T]
    soc_total = [sum(value(vars.soc[h, t]) for h in H) for t in T]

    out = DataFrame(
        timestamp = input_df.timestamp,
        demand_mwh = input_df.demand_mwh,
        pv_cf = input_df.pv_cf,
        wind_cf = input_df.wind_cf,
        weight = input_df.weight,
        p_pv = [value(vars.p_pv[t]) for t in T],
        p_wind = [value(vars.p_wind[t]) for t in T],
        curt_pv = [value(vars.curt_pv[t]) for t in T],
        curt_wind = [value(vars.curt_wind[t]) for t in T],
        p_oil = [value(vars.p_oil[t]) for t in T],
        p_gas = [value(vars.p_gas[t]) for t in T],
        nse = [value(vars.nse[t]) for t in T],
        reserve_shortfall = [value(vars.reserve_shortfall[t]) for t in T],
        charge_total = charge_total,
        discharge_total = discharge_total,
        soc_total = soc_total,
    )

    for h in H
        out[!, Symbol("charge_$(h)")] = [value(vars.charge[h, t]) for t in T]
        out[!, Symbol("discharge_$(h)")] = [value(vars.discharge[h, t]) for t in T]
        out[!, Symbol("soc_$(h)")] = [value(vars.soc[h, t]) for t in T]
    end

    return out
end

function write_summary_csv(path::String, rows)
    # Accept either a vector of named tuples or a prebuilt DataFrame.
    df = rows isa DataFrame ? rows : DataFrame(rows)
    CSV.write(path, df)
    return df
end

function write_dispatch_csv(path::String, dispatch_df::DataFrame)
    CSV.write(path, dispatch_df)
    return dispatch_df
end

function print_base_kpis(row)
    # Compact terminal block for quick run sanity checks.
    println("==================== Base Run ====================")
    @printf("Objective:              %12.2f EUR/yr\n", row.objective_value)
    @printf("  Investment cost:      %12.2f\n", row.investment_cost)
    @printf("  Operating cost:       %12.2f\n", row.operating_cost)
    @printf("    Oil cost:           %12.2f\n", row.oil_cost_total)
    @printf("    Gas cost:           %12.2f\n", row.gas_cost_total)
    @printf("    Carbon component:   %12.2f\n", row.carbon_cost_component)
    @printf("    VoLL component:     %12.2f\n", row.voll_cost_component)
    @printf("    Curtail penalty:    %12.2f\n", row.curtailment_penalty_component)
    @printf("    Reserve penalty:    %12.2f\n", row.reserve_shortfall_penalty_component)

    @printf("Build (MW): PV=%8.2f | Wind=%8.2f | Gas=%8.2f\n", row.dcap_pv, row.dcap_wind, row.dcap_gas)
    @printf("Battery build: P=%8.2f MW | E=%8.2f MWh\n", row.Pbat_total, row.Ebat_total)

    @printf("Reliability: NSE=%10.2f MWh | NSE%%=%7.4f | NSE hours=%5d | Peak NSE=%8.2f MW\n",
        row.total_nse_mwh, row.nse_pct, row.nse_hours, row.peak_nse)

    @printf("Curtailment: total=%10.2f MWh | pct potential=%7.3f\n", row.total_curt, row.curt_pct_of_potential)

    @printf("Reserve shortfall: total=%10.2f MWh | hours=%5d | max=%8.2f MW\n",
        row.total_reserve_shortfall, row.reserve_shortfall_hours, row.max_reserve_shortfall)
    println("==================================================")
end

function print_sensitivity_line(row)
    # One-line progress output per scenario for long sweeps.
    @printf("%s | obj=%.2f | nse%%=%.4f | curt%%=%.3f | dgas=%.2f | batP=%.2f\n",
        row.scenario_name,
        row.objective_value,
        row.nse_pct,
        row.curt_pct_of_potential,
        row.dcap_gas,
        row.Pbat_total,
    )
end
