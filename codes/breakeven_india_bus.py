"""
Mileage breakeven, India heavy vehicle: Switch EiV 12 (12 m electric bus, 283 kWh LFP) vs a 12 m diesel city bus.
D* = dM / (e_ICE - e_EV). Units: kg CO2e and km throughout.
dM counts only the battery; rest-of-vehicle manufacturing is assumed equal for EV and diesel bus.
Every input is a value to verify and cite (see the references list in the chat answer).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------- Inputs ----------
GRID_G_PER_KWH = 705.4     # India grid (g CO2e/kWh), OWID value used in group doc; verify
CHARGE_EFF     = 0.90      # assumption (same as the car/scooter analysis)
TD_LOSS        = 0.17      # assumption
BATT_KG_PER_KWH= 68        # ICCT India battery factor, used for cross-category consistency
DIESEL_KG_PER_L= 2.68      # tailpipe CO2 per litre (assumption)
UPSTREAM       = 1.18      # well-to-tank uplift (assumption)
BATT_KWH       = 283       # Switch EiV 12, LFP (electrive, Sept 2026)
EV_KWH_PER_KM  = 1.0       # real-world energy use at the battery (WRI India ~1.0-1.11 km/kWh; range 0.8-1.3)
DIESEL_KMPL    = 3.0       # real-world diesel economy (WRI India 2.75-3.5 km/L)
LIFETIME_KM    = 864_000   # 72,000 km/yr x 12 yr (e-vehicleinfo TCO model)

def run(batt_kwh=BATT_KWH, batt=BATT_KG_PER_KWH, use=EV_KWH_PER_KM, kmpl=DIESEL_KMPL,
        grid=GRID_G_PER_KWH, n_batt=1, eff=CHARGE_EFF, life=LIFETIME_KM):
    k = use / (eff * (1 - TD_LOSS))                  # kWh generated per km
    e_ev = k * grid / 1000                           # kg/km
    e_ice = DIESEL_KG_PER_L * UPSTREAM / kmpl        # kg/km
    dM = n_batt * batt_kwh * batt                    # kg
    gap = e_ice - e_ev
    d = dM / gap if gap > 0 else float("inf")
    return dict(k=k, e_ev=e_ev, e_ice=e_ice, dM=dM, d_star=d, life=life,
                ev_life_t=(dM + e_ev * life) / 1000, ice_life_t=e_ice * life / 1000)

def sensitivity():
    base = run()
    cases = [("Grid 400 g/kWh", dict(grid=400)), ("Grid 767 g/kWh", dict(grid=767)), ("Grid 1,100 g/kWh", dict(grid=1100)),
             ("Battery 45 kg/kWh (LFP-type)", dict(batt=45)), ("Battery 110 kg/kWh", dict(batt=110)),
             ("Battery 196 kg/kWh (Hawkins-derived)", dict(batt=196)),
             ("One battery replacement (dM x2)", dict(n_batt=2)),
             ("389 kWh NMC pack (earlier EiV 12 spec)", dict(batt_kwh=389)),
             ("EV use 0.8 kWh/km", dict(use=0.8)), ("EV use 1.3 kWh/km", dict(use=1.3)),
             ("Diesel 2.0 km/L", dict(kmpl=2.0)), ("Diesel 2.75 km/L", dict(kmpl=2.75)), ("Diesel 3.5 km/L", dict(kmpl=3.5)),
             ("Charging efficiency 95%", dict(eff=0.95))]
    print(f"Base D* = {base['d_star']:,.0f} km"); rows = [("Base case", base["d_star"])]
    for lbl, kw in cases:
        d = run(**kw)["d_star"]; rows.append((lbl, d))
        print(f"  {lbl:42s} {d:>12,.0f} km  ({d/base['d_star']-1:+.0%})")
    return rows

def plot(fname="fig_cumulative_bus.png"):
    r = run(); km = np.linspace(0, LIFETIME_KM, 300)
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(km / 1000, (r["dM"] + r["e_ev"] * km) / 1000, color="tab:green", label="Electric bus (incl. battery)")
    ax.plot(km / 1000, r["e_ice"] * km / 1000, color="tab:red", label="Diesel bus (well-to-wheel)")
    ax.axvline(r["d_star"] / 1000, color="gray", ls=":")
    ax.annotate(f"breakeven ~{r['d_star']/1000:.0f}k km", (r["d_star"] / 1000, r["e_ice"] * r["d_star"] / 1000),
                xytext=(0.08, 0.85), textcoords="axes fraction", arrowprops=dict(arrowstyle="-", color="gray"))
    ax.set_xlabel("Distance (thousand km)"); ax.set_ylabel("Cumulative emissions (t CO2e)")
    ax.set_title("12 m electric bus vs 12 m diesel bus, India\n(rest-of-vehicle manufacturing assumed equal)")
    ax.legend(loc="lower right"); fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)

if __name__ == "__main__":
    r = run()
    print(f"k = {r['k']:.3f} kWh/km | EV {r['e_ev']*1000:.0f} g/km | diesel {r['e_ice']*1000:.0f} g/km | saving {(r['e_ice']-r['e_ev'])*1000:.0f} g/km")
    print(f"dM = {r['dM']:,.0f} kg | D* = {r['d_star']:,.0f} km = {r['d_star']/LIFETIME_KM:.1%} of {LIFETIME_KM:,} km")
    print(f"Lifetime: EV {r['ev_life_t']:.0f} t vs diesel {r['ice_life_t']:.0f} t ({1-r['ev_life_t']/r['ice_life_t']:.1%} lower)\n")
    sensitivity(); plot(); print("\nSaved fig_cumulative_bus.png")
