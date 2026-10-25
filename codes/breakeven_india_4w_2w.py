"""
Breakeven analysis, India: 4-wheeler (Tata Nexon EV Max vs Nexon petrol) and
2-wheeler (Ola S1 Air 3 kWh vs Honda Activa 6G).

Two metrics per vehicle pair
  1) Mileage breakeven   D* = dM / (e_ICE - e_EV)
  2) Grid threshold      g* = (e_ICE - dM / D) / k       (k = kWh generated per km)

dM counts only the battery (extra EV manufacturing); rest-of-vehicle manufacturing is
assumed equal for EV and ICE. All inputs are values to verify and cite (see README/refs).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------- Shared assumptions ----------
GRID_G_PER_KWH  = 705.4    # India grid, g CO2e/kWh (OWID figure used in group doc; verify year/source)
CHARGE_EFF      = 0.90     # wall-to-battery (assumption)
TD_LOSS         = 0.17     # transmission & distribution loss (assumption, India ~17-18%)
BATT_KG_PER_KWH = 68       # ICCT 2021 India battery factor (kg CO2e/kWh)
PETROL_KG_PER_L = 2.31     # tailpipe CO2 per litre (assumption)
UPSTREAM        = 1.18     # well-to-tank uplift on petrol (assumption)

# ---------- Vehicle profiles ----------
PROFILES = {
  "4W: Nexon EV Max vs Nexon petrol": dict(
      batt_kwh=40.5,           # Autocar Pro (launch report)
      range_km=300,            # real-world range, Autocar India expectation
      ice_kmpl=17.44 / 1.34,   # ARAI 17.44 km/L / ICCT real-world factor 1.34 (~13 km/L)
      lifetime_km=188_000),    # ICCT 2021, India SUV lifetime
  "2W: Ola S1 Air vs Activa 6G": dict(
      batt_kwh=3.0,            # Ola S1 Air 3 kWh variant
      range_km=100,            # real-world "Normal" mode (Smartprix); IDC 125, claimed 151
      ice_kmpl=47.0,           # owner-reported (BikeWale); ARAI claimed up to 59.5
      lifetime_km=120_000),    # Enviraj calculator assumption (secondary source)
}

def ev_k(p):                                   # kWh generated per km driven
    return (p["batt_kwh"] / p["range_km"]) / (CHARGE_EFF * (1 - TD_LOSS))

def analyse(p, grid=GRID_G_PER_KWH, batt=BATT_KG_PER_KWH, n_batt=1, ice_kmpl=None, range_km=None, life=None):
    q = dict(p)
    if range_km: q["range_km"] = range_km
    k = ev_k(q)
    e_ev  = k * grid / 1000                                    # kg/km
    e_ice = PETROL_KG_PER_L * UPSTREAM / (ice_kmpl or p["ice_kmpl"])
    dM    = n_batt * p["batt_kwh"] * batt                      # kg
    D     = life or p["lifetime_km"]
    gap   = e_ice - e_ev
    return dict(k=k, e_ev=e_ev * 1000, e_ice=e_ice * 1000, dM=dM,
                d_star=dM / gap if gap > 0 else float("inf"),
                g_star=(e_ice - dM / D) / k * 1000, life=D)

def table():
    print(f"{'Vehicle pair':36s}{'EV g/km':>9s}{'ICE g/km':>10s}{'dM kg':>8s}{'D* km':>9s}{'D*/life':>9s}{'g* g/kWh':>10s}")
    for name, p in PROFILES.items():
        r = analyse(p)
        print(f"{name:36s}{r['e_ev']:9.1f}{r['e_ice']:10.1f}{r['dM']:8.0f}{r['d_star']:9,.0f}{r['d_star']/r['life']:9.1%}{r['g_star']:10,.0f}")

def sensitivity(name):
    p = PROFILES[name]; base = analyse(p)
    print(f"\nSensitivity of D* for {name} (base {base['d_star']:,.0f} km):")
    cases = [("grid 400 g/kWh", dict(grid=400)), ("grid 767 g/kWh (ICCT-sourced)", dict(grid=767)),
             ("grid 1100 g/kWh (2W paper)", dict(grid=1100)),
             ("battery 50 kg/kWh", dict(batt=50)), ("battery 110 kg/kWh", dict(batt=110)),
             ("battery 196 kg/kWh (Hawkins-derived)", dict(batt=196)),
             ("one battery replacement (dM x2)", dict(n_batt=2))]
    if name.startswith("2W"):
        cases += [("EV range 125 km (IDC/Eco)", dict(range_km=125)), ("EV range 80 km", dict(range_km=80)),
                  ("ICE 59.5 km/L (ARAI claim)", dict(ice_kmpl=59.5)), ("ICE 40 km/L", dict(ice_kmpl=40))]
    else:
        cases += [("EV range 250 km", dict(range_km=250)), ("EV range 437 km (ARAI)", dict(range_km=437)),
                  ("ICE 17.44 km/L (ARAI)", dict(ice_kmpl=17.44))]
    for lbl, kw in cases:
        r = analyse(p, **kw); print(f"  {lbl:40s} D* = {r['d_star']:>10,.0f} km   g* = {r['g_star']:>6,.0f} g/kWh")

def plots():
    # Fig 1: cumulative emissions, one panel per vehicle pair
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, (name, p) in zip(axs, PROFILES.items()):
        r = analyse(p); km = np.linspace(0, r["life"], 200)
        ax.plot(km / 1000, (r["dM"] * 1000 + r["e_ev"] * km) / 1e6, color="tab:green", label="EV (incl. battery)")   # kg->g, then g->t
        ax.plot(km / 1000, r["e_ice"] * km / 1e6, color="tab:red", label="Petrol (well-to-wheel)")
        if np.isfinite(r["d_star"]):
            ax.axvline(r["d_star"] / 1000, color="gray", ls=":")
            ax.annotate(f"breakeven ~{r['d_star']/1000:.1f}k km", (r["d_star"] / 1000, r["e_ice"] * r["d_star"] / 1e6),
                        xytext=(0.08, 0.85), textcoords="axes fraction", arrowprops=dict(arrowstyle="-", color="gray"))
        ax.set_title(name, fontsize=10); ax.set_xlabel("Distance (thousand km)"); ax.set_ylabel("Cumulative emissions (t CO2e)"); ax.legend(fontsize=8)
    fig.suptitle("Cumulative emissions (rest-of-vehicle manufacturing assumed equal)", fontsize=10)
    fig.tight_layout(); fig.savefig("fig_cumulative_4w_2w.png", dpi=150); plt.close(fig)
    # Fig 2: breakeven as % of lifetime vs grid
    gs = np.linspace(20, 1500, 400); fig, ax = plt.subplots(figsize=(8.5, 5))
    for (name, p), c in zip(PROFILES.items(), ["tab:blue", "tab:orange"]):
        y = np.array([analyse(p, grid=g)["d_star"] / p["lifetime_km"] * 100 for g in gs]); y[~np.isfinite(y)] = np.nan
        ax.plot(gs, y, color=c, label=name)
    ax.axhline(100, color="k", ls="--", lw=1, label="end of assumed lifetime")
    ax.axvline(GRID_G_PER_KWH, color="gray", ls=":", label=f"India grid {GRID_G_PER_KWH:.0f} g/kWh")
    ax.set_ylim(0, 150); ax.set_xlabel("Grid carbon intensity (g CO2e/kWh)"); ax.set_ylabel("Breakeven distance (% of lifetime)")
    ax.set_title("How early the EV pays back its battery, by vehicle category"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig("fig_breakeven_vs_grid_4w_2w.png", dpi=150); plt.close(fig)

if __name__ == "__main__":
    table()
    for n in PROFILES: sensitivity(n)
    plots(); print("\nSaved fig_cumulative_4w_2w.png, fig_breakeven_vs_grid_4w_2w.png")
