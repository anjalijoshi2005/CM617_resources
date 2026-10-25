# -*- coding: utf-8 -*-
"""
Created on Sun Oct 25 20:38:59 2026

@author: Shreya
"""

"""
EV vs petrol CO2 break-even calculator
--------------------------------------
"EV vs petrol: CO2 break-even by vehicle type and country".

Break-even distance (km) = battery manufacturing CO2 / (petrol g/km - EV g/km)
Break-even time (years)  = break-even distance / annual km
Grid data: Our World in Data energy dataset (column `carbon_intensity_elec`,
lifecycle g CO2e per kWh generated, sourced by OWID from Ember).
"""

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Constants and assumptions
# ---------------------------------------------------------------------------
OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
GRID_YEAR = 2025

GAL_TO_L = 3.78541
TAILPIPE_G_PER_GAL = 8887       # EPA: tailpipe CO2 per US gallon of gasoline
UPSTREAM_FACTOR = 1.25          # EPA: adds drilling, refining, transport
PETROL_G_PER_L = TAILPIPE_G_PER_GAL / GAL_TO_L * UPSTREAM_FACTOR   # ~2,935 g/L

BATTERY_KG_PER_KWH = 70         # ICCT 2021: 60 (Europe), 68 (China/India); rounded up
CHARGING_EFFICIENCY = 0.90      # assumption: ~10% charging losses
DEFAULT_GRID_LOSS = 0.06        # assumption for grids other than India
GRID_LOSS = {"India": 0.177}    # CEA all-India T&D losses (via RBI)

# ---------------------------------------------------------------------------
# 2. Vehicle pairs (real-world road-test figures)
#    battery_kwh        : EV battery capacity
#    ev_kwh_per_km      : battery-to-wheel energy use (before charging losses)
#    petrol_km_per_l    : petrol version, real-world mixed driving
#    annual_km          : standard annual mileage used in every country
# ---------------------------------------------------------------------------
VEHICLES = {
    # TVS iQube 3.5 kWh (~115 km real range) vs Honda Activa 110 (~50 km/L)
    "Scooter":      dict(battery_kwh=3.5, ev_kwh_per_km=3.5 / 115, petrol_km_per_l=50.0, annual_km=8_800),
    # Tata Tiago EV 24 kWh (7.77 km/kWh) vs Tiago 1.2 petrol (~15 km/L)
    "Hatchback":    dict(battery_kwh=24,  ev_kwh_per_km=1 / 7.77,  petrol_km_per_l=15.0, annual_km=12_000),
    # Tata Harrier EV AWD 75 kWh (401 km) vs Harrier 1.5 turbo-petrol AT (9.33 km/L)
    "Mid-size SUV": dict(battery_kwh=75,  ev_kwh_per_km=75 / 401,  petrol_km_per_l=9.33, annual_km=12_000),
}

COUNTRIES = ["India", "Poland", "China", "Japan", "United States",
             "Germany", "United Kingdom", "France", "Norway"]

# Fallback values (OWID 2025) in case the download fails
FALLBACK_GRID = {"India": 670, "Poland": 589, "China": 525, "Japan": 477,
                 "United States": 384, "Germany": 330, "United Kingdom": 217,
                 "France": 41, "Norway": 28}


# ---------------------------------------------------------------------------
# 3. Load grid carbon intensity from OWID
# ---------------------------------------------------------------------------
def load_grid_intensity(year=GRID_YEAR):
    """Return {country: g CO2e per kWh generated} for the chosen year."""
    try:
        df = pd.read_csv(OWID_URL, usecols=["country", "year", "carbon_intensity_elec"])
        df = df[(df.year == year) & (df.country.isin(COUNTRIES))]
        grid = dict(zip(df.country, df.carbon_intensity_elec.round()))
        missing = [c for c in COUNTRIES if c not in grid or pd.isna(grid[c])]
        if missing:
            raise ValueError(f"No {year} data for: {missing}")
        print(f"Loaded OWID grid intensity for {year}.")
        return grid
    except Exception as e:
        print(f"OWID download failed ({e}); using built-in 2025 values.")
        return FALLBACK_GRID


# ---------------------------------------------------------------------------
# 4. Core calculation
# ---------------------------------------------------------------------------
def break_even(vehicle, grid_g_per_kwh, grid_loss,
               battery_kg_per_kwh=BATTERY_KG_PER_KWH, petrol_km_per_l=None):
    """Return a dict with per-km emissions and break-even distance/time."""
    v = vehicle
    km_per_l = petrol_km_per_l or v["petrol_km_per_l"]

    # EV: energy drawn from the socket x carbon intensity at the plug
    ev_kwh_at_plug = v["ev_kwh_per_km"] / CHARGING_EFFICIENCY
    grid_at_plug = grid_g_per_kwh / (1 - grid_loss)
    ev_g_per_km = ev_kwh_at_plug * grid_at_plug

    # Petrol: well-to-wheel emissions per km
    petrol_g_per_km = PETROL_G_PER_L / km_per_l

    # Battery manufacturing "debt" in grams
    battery_debt_g = v["battery_kwh"] * battery_kg_per_kwh * 1000

    saving = petrol_g_per_km - ev_g_per_km
    be_km = battery_debt_g / saving if saving > 0 else float("inf")

    return dict(ev_g_km=ev_g_per_km, petrol_g_km=petrol_g_per_km,
                cut_pct=saving / petrol_g_per_km * 100,
                break_even_km=be_km, break_even_yrs=be_km / v["annual_km"])


# ---------------------------------------------------------------------------
# 5. Main results table
# ---------------------------------------------------------------------------
def main_results(grid):
    rows = []
    for vname, v in VEHICLES.items():
        for c in COUNTRIES:
            r = break_even(v, grid[c], GRID_LOSS.get(c, DEFAULT_GRID_LOSS))
            rows.append(dict(vehicle=vname, country=c, grid_g_kwh=grid[c], **r))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 6. Sensitivity analysis
# ---------------------------------------------------------------------------
HIGHWAY_KMPL = {"Scooter": 55, "Hatchback": 16.6, "Mid-size SUV": 12.49}
ARAI_KMPL = {"Scooter": 59.5, "Hatchback": 19.0, "Mid-size SUV": 16.8}

SCENARIOS = {
    "Base (70 kg/kWh, real-world mixed petrol)": dict(batt=70,  kmpl=None),
    "Battery 50 kg/kWh":                         dict(batt=50,  kmpl=None),
    "Battery 100 kg/kWh":                        dict(batt=100, kmpl=None),
    "Petrol at highway mileage":                 dict(batt=70,  kmpl=HIGHWAY_KMPL),
    "Highway petrol + 100 kg/kWh":               dict(batt=100, kmpl=HIGHWAY_KMPL),
    "Petrol at ARAI-claimed mileage":            dict(batt=70,  kmpl=ARAI_KMPL),
}


def sensitivity(grid, countries=("India", "United States", "Germany")):
    rows = []
    for sname, s in SCENARIOS.items():
        row = {"scenario": sname}
        for vname, v in VEHICLES.items():
            kmpl = s["kmpl"][vname] if s["kmpl"] else None
            vals = []
            for c in countries:
                r = break_even(v, grid[c], GRID_LOSS.get(c, DEFAULT_GRID_LOSS),
                               battery_kg_per_kwh=s["batt"], petrol_km_per_l=kmpl)
                vals.append(f"{r['break_even_km'] / 1000:.1f}k")
            row[vname] = " / ".join(vals)
        rows.append(row)
    return pd.DataFrame(rows)


def mileage_sensitivity(results, factors=(0.6, 1.0, 1.5)):
    """Break-even years at 60%, 100% and 150% of the standard annual mileage."""
    out = results[["vehicle", "country", "break_even_km"]].copy()
    for f in factors:
        annual = out.vehicle.map(lambda v: VEHICLES[v]["annual_km"] * f)
        out[f"yrs_at_{int(f * 100)}pct"] = (out.break_even_km / annual).round(1)
    return out.drop(columns="break_even_km")


# ---------------------------------------------------------------------------
# 7. Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pd.set_option("display.width", 140)
    print(f"Petrol well-to-wheel factor: {PETROL_G_PER_L:.0f} g CO2e/L\n")

    grid = load_grid_intensity()
    res = main_results(grid)

    print("\n=== Per-km emissions and break-even ===")
    print(res.assign(
        ev_g_km=res.ev_g_km.round(0),
        petrol_g_km=res.petrol_g_km.round(0),
        cut_pct=res.cut_pct.round(0),
        break_even_km=res.break_even_km.round(-2),
        break_even_yrs=res.break_even_yrs.round(1),
    ).to_string(index=False))

    print("\n=== Sensitivity: break-even km (India / US / Germany) ===")
    print(sensitivity(grid).to_string(index=False))

    print("\n=== Mileage sensitivity: break-even years ===")
    print(mileage_sensitivity(res).to_string(index=False))

    res.to_csv("ev_breakeven_results.csv", index=False)
    print("\nSaved full results to ev_breakeven_results.csv")