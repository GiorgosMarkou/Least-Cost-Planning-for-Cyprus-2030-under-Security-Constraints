#!/usr/bin/env julia

using CSV
using DataFrames
using JuMP
using HiGHS

include(joinpath(@__DIR__, "params.jl"))
include(joinpath(@__DIR__, "io.jl"))
include(joinpath(@__DIR__, "model.jl"))
include(joinpath(@__DIR__, "outputs.jl"))

function main()
    if length(ARGS) > 1
        error("Usage: julia --project=. model/run_sensitivity.jl [path/to/timeseries_2019_2030_scaled.csv]")
    end

    # Optional CLI override: julia --project=. model/run_sensitivity.jl path/to/file.csv
    cli_path = isempty(ARGS) ? nothing : ARGS[1]
    input_path = resolve_timeseries_path(cli_path)

    if !isfile(input_path)
        error("Input file not found: $input_path\nDefault expected path: $(joinpath(project_root(), DEFAULT_TIMESERIES_RELATIVE))")
    end

    println("Input timeseries: $input_path")

    # Load once; all scenarios reuse the same hourly input table.
    df = load_timeseries(input_path)

    rows = NamedTuple[]
    scenario_id = 1

    # Full Cartesian sweep across oil factor, VoLL, and carbon tax.
    for oil_factor in OIL_FACTOR_LEVELS
        for voll in VOLL_GRID
            for carbon_tax in CARBON_TAX_GRID
                scenario_name = make_scenario_name(oil_factor, voll, carbon_tax)
                params = build_params(oil_factor=oil_factor, voll=voll, carbon_tax=carbon_tax)
                bundle = build_model(df, params, BATTERY_DURATIONS)
                solve_model!(bundle.model)
                row = build_summary_row(bundle, params; scenario_id=scenario_id, scenario_name=scenario_name)
                push!(rows, row)
                print_sensitivity_line(row)
                scenario_id += 1
            end
        end
    end

    # One combined sensitivity summary file.
    out_dir = joinpath(project_root(), "outputs")
    mkpath(out_dir)

    sensitivity_results_path = joinpath(out_dir, "sensitivity_results.csv")

    result_df = write_summary_csv(sensitivity_results_path, rows)

    expected_rows = expected_sensitivity_rows()
    if nrow(result_df) != expected_rows
        error("Sensitivity row count mismatch. Expected $expected_rows, got $(nrow(result_df)).")
    end

    println("Wrote: $sensitivity_results_path")
    println("Scenario rows: $(nrow(result_df))")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
