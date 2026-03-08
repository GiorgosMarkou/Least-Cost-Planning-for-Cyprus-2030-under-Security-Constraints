from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DEMAND_FILE = DATA_DIR / "Ημερήσια Παραγωγή Ηλεκτρικού Συστήματος - 2019.xlsx.xls"
PV_FILE = DATA_DIR / "ninja_pv_34.8824_33.3914_corrected.csv"
WIND_FILE = DATA_DIR / "ninja_wind_34.8824_33.3914_corrected.csv"
OUTPUT_FILE = DATA_DIR / "timeseries_2019_2030_scaled.csv"

TARGET_2030_PEAK_MW = 1583.0


def read_hourly_demand(path: Path) -> pd.DataFrame:
    """Read 15-min demand data and convert to hourly mean demand."""
    df_raw = pd.read_excel(path, sheet_name="2019", header=None)

    df = df_raw.iloc[4:].copy()
    df = df[[0, 6]].copy()
    df.columns = ["timestamp", "demand2019"]

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["demand2019"] = pd.to_numeric(df["demand2019"], errors="coerce")
    df = df.dropna(subset=["timestamp", "demand2019"]).copy()

    df["timestamp_hour"] = df["timestamp"].dt.floor("h")
    hourly = (
        df.groupby("timestamp_hour", as_index=False)["demand2019"]
        .mean()
        .rename(columns={"timestamp_hour": "timestamp"})
        .sort_values("timestamp")
    )

    return hourly


def fill_missing_hours(hourly: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Reindex to full-year hourly timeline and interpolate missing demand hours."""
    year = int(hourly["timestamp"].dt.year.mode().iloc[0])
    full_hours = pd.date_range(
        start=f"{year}-01-01 00:00:00",
        end=f"{year}-12-31 23:00:00",
        freq="h",
    )

    hourly = hourly.set_index("timestamp").reindex(full_hours)
    missing_before = int(hourly["demand2019"].isna().sum())

    if missing_before > 0:
        hourly["demand2019"] = hourly["demand2019"].interpolate(method="time")
        hourly["demand2019"] = hourly["demand2019"].ffill().bfill()

    hourly = hourly.rename_axis("timestamp").reset_index()
    return hourly, missing_before


def read_ninja_cf(
    path: Path, output_col: str, target_index: pd.DatetimeIndex
) -> tuple[pd.DataFrame, int]:
    """Read Renewables.ninja CF, convert UTC to local time, and align to target index."""
    df = pd.read_csv(path, skiprows=3)
    # Renewables.ninja timestamps are UTC; convert to Cyprus local clock.
    df["timestamp"] = (
        pd.to_datetime(df["time"], errors="coerce", utc=True)
        .dt.tz_convert("Europe/Nicosia")
        .dt.tz_localize(None)
    )
    df[output_col] = pd.to_numeric(df["electricity"], errors="coerce")

    aligned = (
        df[["timestamp", output_col]]
        .dropna()
        .groupby("timestamp", as_index=False)[output_col]
        .mean()
        .sort_values("timestamp")
        .set_index("timestamp")
        .reindex(target_index)
    )

    missing_before = int(aligned[output_col].isna().sum())
    if missing_before > 0:
        aligned[output_col] = aligned[output_col].interpolate(method="time")
        aligned[output_col] = aligned[output_col].ffill().bfill()

    aligned = aligned.rename_axis("timestamp").reset_index()
    return aligned, missing_before


def main() -> None:
    hourly_demand = read_hourly_demand(DEMAND_FILE)
    hourly_demand, missing_hours_filled = fill_missing_hours(hourly_demand)

    peak_2019 = hourly_demand["demand2019"].max()
    scale_factor = TARGET_2030_PEAK_MW / peak_2019
    hourly_demand["demand2030"] = hourly_demand["demand2019"] * scale_factor

    target_index = pd.DatetimeIndex(hourly_demand["timestamp"])
    pv, missing_pv_filled = read_ninja_cf(PV_FILE, "pv_cf", target_index)
    wind, missing_wind_filled = read_ninja_cf(WIND_FILE, "wind_cf", target_index)

    out = (
        hourly_demand.merge(pv, on="timestamp", how="left")
        .merge(wind, on="timestamp", how="left")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    missing_pv = int(out["pv_cf"].isna().sum())
    missing_wind = int(out["wind_cf"].isna().sum())
    if missing_pv or missing_wind:
        raise ValueError(
            "Timestamp alignment failed after merge: "
            f"missing pv={missing_pv}, missing wind={missing_wind}"
        )

    out.to_csv(OUTPUT_FILE, index=False)

    print(f"Missing demand hours filled: {missing_hours_filled}")
    print(f"Peak hourly demand 2019: {peak_2019:.6f}")
    print(f"Scale factor: {scale_factor:.6f}")
    print(f"Peak hourly demand 2030: {out['demand2030'].max():.6f}")
    print(f"Missing PV hours filled (UTC->local alignment): {missing_pv_filled}")
    print(f"Missing wind hours filled (UTC->local alignment): {missing_wind_filled}")
    print(f"Rows written: {len(out)}")
    print(f"Saved: {OUTPUT_FILE}")
    print("\nFirst rows:")
    print(out.head())


if __name__ == "__main__":
    main()
