"""
Breakeven for Tata Nexon EV Max vs Nexon petrol (India).
1) Mileage breakeven   D* = dM / (e_ICE - e_EV)
2) Grid-intensity threshold g* = (e_ICE - dM/D) / k
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")            # saves PNGs; no display needed
import matplotlib.pyplot as plt

# ---------------- Inputs ----------------
# EV
BATT_KWH        = 40.5       # usable battery (kWh)
REAL_RANGE_KM   = 300        # real-world range (km)
CHARGE_EFF      = 0.90       # wall-to-battery efficiency
TD_LOSS         = 0.17       # transmission & distribution loss (India ~17-18%)
BATT_KG_PER_KWH = 68         # battery manufacturing (ICCT India factor), kg CO2e/kWh
GRID_G_PER_KWH  = 705.4      # grid intensity (g CO2e/kWh); check source/year
# ICE
ARAI_KMPL       = 17.44      # certified fuel economy (km/L)
REALWORLD_FACTOR= 1.34       # ICCT real-world factor for India
PETROL_KG_PER_L = 2.31       # tailpipe CO2 per litre
UPSTREAM        = 1.18       # well-to-tank uplift
# Use
LIFETIME_KM     = 188_000    # ICCT SUV lifetime for India
# -----------------------------------------

def ev_emission_per_km(grid_g_per_kwh=GRID_G_PER_KWH, range_km=REAL_RANGE_KM):
    c_batt = BATT_KWH / range_km                          # kWh/km at battery
    k = c_batt / (CHARGE_EFF * (1 - TD_LOSS))             # kWh generated per km
    return k * grid_g_per_kwh / 1000, k                   # (kg/km, kWh/km)

def ice_emission_per_km(kmpl=ARAI_KMPL / REALWORLD_FACTOR):
    return PETROL_KG_PER_L * UPSTREAM / kmpl              # kg/km, well-to-wheel

def breakeven_distance(dM, e_ice, e_ev):
    gap = e_ice - e_ev
    return dM / gap if gap > 0 else float("inf")          # inf = EV never catches up

def grid_threshold(dM, e_ice, k, life_km=LIFETIME_KM, include_mfg=True):
    m = dM if include_mfg else 0.0
    return (e_ice - m / life_km) / k * 1000               # g/kWh


# ---------------- Plots ----------------
def plot_cumulative(dM, e_ev, e_ice, fname="plot_cumulative.png"):
    """Cumulative emissions vs distance; crossing point = mileage breakeven."""
    km = np.linspace(0, LIFETIME_KM, 300)
    ev = (dM + e_ev * km) / 1000                          # t CO2e (extra EV mfg + use)
    ice = (e_ice * km) / 1000
    d_star = breakeven_distance(dM, e_ice, e_ev)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(km / 1000, ev, label=f"EV ({GRID_G_PER_KWH:.0f} g/kWh grid) incl. battery", color="tab:green")
    ax.plot(km / 1000, ice, label="Petrol (well-to-wheel)", color="tab:red")
    if np.isfinite(d_star):
        ax.axvline(d_star / 1000, color="gray", ls=":")
        ax.scatter([d_star / 1000], [e_ice * d_star / 1000], color="k", zorder=3)
        ax.annotate(f"breakeven ~{d_star/1000:.0f}k km", (d_star / 1000, e_ice * d_star / 1000),
                    xytext=(10, -25), textcoords="offset points")
    ax.set_xlabel("Distance (thousand km)"); ax.set_ylabel("Cumulative emissions (t CO2e)")
    ax.set_title("Nexon EV Max vs petrol Nexon: cumulative emissions\n(rest-of-vehicle manufacturing assumed equal)")
    ax.legend(); fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)

def plot_vs_grid(dM, e_ice, k, fname="plot_breakeven_vs_grid.png"):
    """Breakeven distance vs grid intensity, with the grid threshold and India value marked."""
    gs = np.linspace(20, 1400, 400)
    d = np.array([breakeven_distance(dM, e_ice, k * g / 1000) for g in gs])
    d[~np.isfinite(d)] = np.nan
    g_thr = grid_threshold(dM, e_ice, k)
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(gs, d / 1000, color="tab:blue")
    ax.axhline(LIFETIME_KM / 1000, color="k", ls="--", lw=1, label=f"assumed lifetime {LIFETIME_KM:,} km")
    ax.axvline(GRID_G_PER_KWH, color="tab:orange", ls=":", label=f"India grid {GRID_G_PER_KWH:.0f} g/kWh")
    ax.axvline(g_thr, color="tab:red", ls=":", label=f"grid threshold ~{g_thr:.0f} g/kWh")
    ax.set_ylim(0, 400)
    ax.set_xlabel("Grid carbon intensity (g CO2e/kWh)"); ax.set_ylabel("Breakeven distance (thousand km)")
    ax.set_title("Mileage breakeven vs grid intensity"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)

if __name__ == "__main__":
    dM = BATT_KWH * BATT_KG_PER_KWH                       # extra EV manufacturing (battery only)
    e_ev, k = ev_emission_per_km()
    e_ice = ice_emission_per_km()

    print(f"EV   : {e_ev*1000:6.1f} g/km   (generated energy {k:.3f} kWh/km)")
    print(f"ICE  : {e_ice*1000:6.1f} g/km   (real-world {ARAI_KMPL/REALWORLD_FACTOR:.1f} km/L)")
    print(f"Extra EV manufacturing dM: {dM:,.0f} kg")
    print(f"\nMileage breakeven D*       : {breakeven_distance(dM, e_ice, e_ev):,.0f} km")
    print(f"Grid threshold g* ({LIFETIME_KM:,} km) with mfg   : {grid_threshold(dM, e_ice, k):,.0f} g/kWh")
    print(f"Grid threshold g* without mfg            : {grid_threshold(dM, e_ice, k, include_mfg=False):,.0f} g/kWh")

    print("\nBreakeven distance vs grid intensity:")
    for g in (30, 200, 400, 705, 767, 1100):
        e, _ = ev_emission_per_km(g)
        print(f"  {g:5d} g/kWh -> {breakeven_distance(dM, e_ice, e):>10,.0f} km")

    plot_cumulative(dM, e_ev, e_ice)
    plot_vs_grid(dM, e_ice, k)
    print("\nSaved plot_cumulative.png and plot_breakeven_vs_grid.png")
