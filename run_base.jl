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
        error("Usage: julia --project=. model/run_base.jl [path/to/timeseries_2019_2030_scaled.csv]")
    end

    # Optional CLI override: julia --project=. model/run_base.jl path/to/file.csv
    cli_path = isempty(ARGS) ? nothing : ARGS[1]
    input_path = resolve_timeseries_path(cli_path)

    if !isfile(input_path)
        error("Input file not found: $input_path\nDefault expected path: $(joinpath(project_root(), DEFAULT_TIMESERIES_RELATIVE))")
    end

    println("Input timeseries: $input_path")

    # Load inputs, build model, solve once for the base settings.
    df = load_timeseries(input_path)
    params = build_params(
        oil_factor = DEFAULT_OIL_FACTOR,
        voll = DEFAULT_VOLL,
        carbon_tax = DEFAULT_CARBON_TAX,
    )

    bundle = build_model(df, params, BATTERY_DURATIONS)
    solve_model!(bundle.model)

    row = build_summary_row(bundle, params; scenario_id=1, scenario_name="base")

    # All outputs from this runner are written under outputs/.
    out_dir = joinpath(project_root(), "outputs")
    mkpath(out_dir)

    base_results_path = joinpath(out_dir, "base_results.csv")
    base_dispatch_path = joinpath(out_dir, "base_dispatch.csv")

    write_summary_csv(base_results_path, [row])
    write_dispatch_csv(base_dispatch_path, build_dispatch_table(df, bundle))

    print_base_kpis(row)

    println("Wrote: $base_results_path")
    println("Wrote: $base_dispatch_path")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
