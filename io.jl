using CSV
using DataFrames
using Dates

# Return the first column name that exists from a small alias list.
# We keep aliases short and explicit so input requirements stay clear.
function _find_column(df::DataFrame, candidates::Vector{String})
    for name in candidates
        if name in names(df)
            return name
        end
    end
    return nothing
end

# Strict numeric parsing for required columns.
# Fails fast with row index so data issues are easy to debug.
function _require_numeric_column(df::DataFrame, col::String)
    values = df[!, col]
    out = Vector{Float64}(undef, length(values))
    for i in eachindex(values)
        v = values[i]
        if v isa Missing
            error("Column '$col' has missing value at row $i")
        end
        try
            out[i] = Float64(v)
        catch
            error("Column '$col' must be numeric. Bad value at row $i: $(repr(v))")
        end
    end
    return out
end

# Parse numeric columns that may include missing values.
# Missing handling is done in a separate step so the rule is visible.
function _numeric_or_missing_column(df::DataFrame, col::String)
    values = df[!, col]
    out = Vector{Union{Missing,Float64}}(undef, length(values))
    for i in eachindex(values)
        v = values[i]
        if v isa Missing
            out[i] = missing
            continue
        end
        try
            out[i] = Float64(v)
        catch
            error("Column '$col' must be numeric. Bad value at row $i: $(repr(v))")
        end
    end
    return out
end

# Fill isolated missing values with nearest-neighbor logic.
# This is deliberately deterministic; unresolved gaps error out.
function _fill_missing_with_neighbors!(values::Vector{Union{Missing,Float64}}, col::String)
    missing_idx = findall(ismissing, values)
    if isempty(missing_idx)
        return Float64.(values)
    end

    n = length(values)
    for i in missing_idx
        prev = i > 1 ? values[i - 1] : missing
        nxt = i < n ? values[i + 1] : missing
        if !ismissing(prev) && !ismissing(nxt)
            values[i] = (prev + nxt) / 2
        elseif !ismissing(prev)
            values[i] = prev
        elseif !ismissing(nxt)
            values[i] = nxt
        end
    end

    unresolved = findall(ismissing, values)
    if !isempty(unresolved)
        error("Column '$col' still has missing values after interpolation.")
    end
    return Float64.(values)
end

# Accept either an explicit timestamp column or (year, hour_of_year).
# This keeps the loader compatible with common hourly-export formats.
function _require_timestamp_column(df::DataFrame)
    if "timestamp" in names(df)
        ts = df[!, "timestamp"]
        if any(ismissing, ts)
            error("Column 'timestamp' has missing values")
        end
        return collect(ts)
    end

    # Alternative format used by some hourly exports.
    if ("year" in names(df)) && ("hour_of_year" in names(df))
        years = _require_numeric_column(df, "year")
        hours = _require_numeric_column(df, "hour_of_year")
        ts = Vector{DateTime}(undef, nrow(df))
        for i in 1:nrow(df)
            y = Int(round(years[i]))
            h = Int(round(hours[i]))
            ts[i] = DateTime(y, 1, 1, 0, 0, 0) + Hour(h - 1)
        end
        return ts
    end

    error("Missing required timestamp information. Provide 'timestamp' or ('year' and 'hour_of_year').")
end

# Main CSV loader for the optimisation inputs.
# Validation is intentionally narrow: required columns + numeric checks.
function load_timeseries(path::String)
    if !isfile(path)
        error("Timeseries file not found: $path")
    end

    raw = CSV.read(path, DataFrame)
    if nrow(raw) == 0
        error("Timeseries file is empty: $path")
    end

    demand_col = _find_column(raw, ["demand2030", "demand_mwh_2030", "demand_mwh", "demand_MWh", "demand", "demand2019"])
    pv_col = _find_column(raw, ["pv_cf", "pvCF", "pv_cf_hourly"])
    wind_col = _find_column(raw, ["wind_cf", "windCF", "wind_cf_hourly"])

    missing_required = String[]
    if demand_col === nothing
        push!(missing_required, "demand2030|demand_mwh_2030|demand_mwh|demand_MWh|demand|demand2019")
    end
    if pv_col === nothing
        push!(missing_required, "pv_cf|pvCF|pv_cf_hourly")
    end
    if wind_col === nothing
        push!(missing_required, "wind_cf|windCF|wind_cf_hourly")
    end
    if !isempty(missing_required)
        error("Missing required input columns: $(join(missing_required, ", "))")
    end

    timestamp = _require_timestamp_column(raw)
    demand = _require_numeric_column(raw, demand_col)
    pv_cf = _fill_missing_with_neighbors!(_numeric_or_missing_column(raw, pv_col), pv_col)
    wind_cf = _fill_missing_with_neighbors!(_numeric_or_missing_column(raw, wind_col), wind_col)
    weight = if "weight" in names(raw)
        _require_numeric_column(raw, "weight")
    else
        fill(1.0, nrow(raw))
    end

    return DataFrame(
        timestamp = timestamp,
        demand_mwh = demand,
        pv_cf = pv_cf,
        wind_cf = wind_cf,
        weight = weight,
    )
end
