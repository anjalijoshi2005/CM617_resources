import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. LOAD ALL THE REAL DATASETS
# ==========================================
print("Loading all datasets... (This might take a moment)")
df_grid = pd.read_csv("lifecycle-carbon-intensity-of-electricity.csv")
df_vehicles = pd.read_csv("Vehicle Efficiency Dataset.csv", low_memory=False)
df_ev_raw = pd.read_excel("EV data by country 2026.xlsx", sheet_name="GEVO_EV_2026")
df_energy = pd.read_excel("Global Energy Mix Dataset.xlsx", sheet_name="data")
df_co2 = pd.read_csv("Global CO₂ Emissions Dataset_2.csv")

# ==========================================
# 2. BASELINE: GET REAL VEHICLE EFFICIENCY DATA
# ==========================================
avg_petrol_mpg = df_vehicles[df_vehicles['fuelType1'] == 'Regular Gasoline']['comb08'].mean()
petrol_liters_per_km = (235.214 / avg_petrol_mpg) / 100 
petrol_running_co2 = petrol_liters_per_km * 2.31  # kg CO2/km

evs = df_vehicles[df_vehicles['fuelType1'] == 'Electricity']
avg_ev_kwh_per_100_miles = evs[evs['combE'] > 0]['combE'].mean()
ev_kwh_per_km = avg_ev_kwh_per_100_miles / 160.934  # kWh/km

avg_diesel_mpg = df_vehicles[df_vehicles['fuelType1'] == 'Diesel']['comb08'].mean()
diesel_running_co2 = ((235.214 / avg_diesel_mpg) / 100) * 2.68  # kg CO2/km

# --- DATA CLEANING FOR MERGES ---
# Standardize country names across datasets so they don't drop out during merges
country_mapping = {
    'USA': 'United States',
    'UK': 'United Kingdom',
    'Korea': 'South Korea',
    'Russian Federation': 'Russia'
}
df_ev_raw['region_country'] = df_ev_raw['region_country'].replace(country_mapping)


# ==========================================
# ANALYSIS 0: BASIC COUNTRY BREAK-EVEN
# ==========================================
print("\n" + "="*60)
print("BASELINE: EV VS PETROL LIFECYCLE BREAK-EVEN BY COUNTRY")
print("="*60)

recent_year = df_grid['Year'].max()
df_recent_grid = df_grid[df_grid['Year'] == recent_year]
countries_to_analyze = ['India', 'United States', 'Norway']

grid_intensities = {}
for country in countries_to_analyze:
    country_data = df_recent_grid[df_recent_grid['Entity'] == country]
    if not country_data.empty:
        grid_intensities[country] = country_data['Carbon intensity'].values[0] / 1000

ev_mfg_co2 = 12000     
petrol_mfg_co2 = 7000  
kilometers = np.linspace(0, 150000, 100)
petrol_total_co2 = petrol_mfg_co2 + (petrol_running_co2 * kilometers)

print("--- RAW GRAPH DATA FOR EXTRACTION ---")
print(f"X-Axis (Distance): 0 to 150,000 km")
print(f"Petrol Y-Axis Start (Mfg): {petrol_total_co2[0]:.0f} kg | End: {petrol_total_co2[-1]:.0f} kg")

plt.figure(figsize=(10, 6))
plt.plot(kilometers, petrol_total_co2, label='Petrol Car', color='black', linewidth=3)
colors = {'India': 'red', 'United States': 'orange', 'Norway': 'green'}

for country, grid_co2_per_kwh in grid_intensities.items():
    ev_running_co2 = ev_kwh_per_km * grid_co2_per_kwh
    ev_total_co2 = ev_mfg_co2 + (ev_running_co2 * kilometers)
    plt.plot(kilometers, ev_total_co2, label=f'EV in {country}', color=colors[country], linewidth=2)
    print(f"EV in {country} Y-Axis Start (Mfg): {ev_total_co2[0]:.0f} kg | End: {ev_total_co2[-1]:.0f} kg")

plt.title('EV vs Petrol: Lifecycle CO2 Break-Even by Country')
plt.xlabel('Distance Driven (km)')
plt.ylabel('Total CO2 Emissions (kg)')
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 1: THE VEHICLE SIZE PARADOX
# ==========================================
print("\n" + "="*60)
print("INSIGHT 1: THE IMPACT OF VEHICLE SIZE (SUV vs SEDAN)")
print("="*60)

is_suv = df_vehicles['VClass'].str.contains('Utility', na=False)
is_car = df_vehicles['VClass'].str.contains('Cars', na=False)

petrol_suvs = df_vehicles[(df_vehicles['fuelType1'] == 'Regular Gasoline') & is_suv]['comb08'].mean()
petrol_cars = df_vehicles[(df_vehicles['fuelType1'] == 'Regular Gasoline') & is_car]['comb08'].mean()
petrol_suv_co2 = ((235.214 / petrol_suvs) / 100) * 2.31
petrol_car_co2 = ((235.214 / petrol_cars) / 100) * 2.31

ev_suvs = df_vehicles[(df_vehicles['fuelType1'] == 'Electricity') & is_suv]['combE'].mean()
ev_cars = df_vehicles[(df_vehicles['fuelType1'] == 'Electricity') & is_car]['combE'].mean()
ev_suv_kwh = ev_suvs / 160.934
ev_car_kwh = ev_cars / 160.934

india_grid_intensity = 0.700 
ev_suv_in_india_co2 = ev_suv_kwh * india_grid_intensity

print("--- THEORETICAL INSIGHT ---")
print("If you drive an Electric SUV in a coal-heavy country (like India), it emits more CO2")
print("than a small, efficient Petrol Sedan due to massive battery weight and grid intensity.")

labels = ['Petrol Sedan', 'Petrol SUV', 'EV Sedan (India)', 'EV SUV (India)']
co2_values = [petrol_car_co2, petrol_suv_co2, (ev_car_kwh*india_grid_intensity), ev_suv_in_india_co2]

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
for lbl, val in zip(labels, co2_values):
    print(f"{lbl}: {val:.3f} kg CO2/km")

plt.figure(figsize=(8, 5))
plt.bar(labels, co2_values, color=['gray', 'black', 'lightgreen', 'darkred'])
plt.title('Vehicle Size: CO2 per km (Including Coal-Grid Emissions)')
plt.ylabel('kg CO2 per km')
plt.grid(axis='y', linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 2: THE GREENING GRID TREND
# ==========================================
print("\n" + "="*60)
print("INSIGHT 2: THE GREENING GRID (DYNAMIC BREAK-EVEN)")
print("="*60)
print("--- THEORETICAL INSIGHT ---")
print("Because grids are getting cleaner, an EV's break-even point shrinks every year.")

countries_to_plot = ['India', 'United States', 'Norway', 'China']
plt.figure(figsize=(10, 6))

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
for country in countries_to_plot:
    country_history = df_grid[(df_grid['Entity'] == country) & (df_grid['Year'] >= 2000)].sort_values('Year')
    if not country_history.empty:
        years = country_history['Year'].tolist()
        intensity = country_history['Carbon intensity'].tolist()
        plt.plot(years, intensity, label=country, linewidth=2)
        print(f"{country} - Year 2000: {intensity[0]:.1f} g/kWh | Latest Year: {intensity[-1]:.1f} g/kWh")

plt.title('Grid Carbon Intensity Over Time (2000 - Present)')
plt.xlabel('Year')
plt.ylabel('Carbon Intensity (grams CO2 per kWh)')
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 3: THE CLIMATE ALIGNMENT MISMATCH
# ==========================================
print("\n" + "="*60)
print("INSIGHT 3: THE CLIMATE ALIGNMENT MISMATCH")
print("="*60)

df_ev_cars = df_ev_raw[(df_ev_raw['parameter'] == 'EV stock') & (df_ev_raw['mode'] == 'Cars') & (df_ev_raw['powertrain'] == 'BEV')]
latest_ev_year = df_ev_cars['year'].max()
df_ev_latest = df_ev_cars[df_ev_cars['year'] == latest_ev_year]
ev_stock_by_country = df_ev_latest.groupby('region_country')['value'].sum().reset_index()
ev_stock_by_country.rename(columns={'region_country': 'Country', 'value': 'Total_EVs'}, inplace=True)

df_alignment = pd.merge(ev_stock_by_country, df_recent_grid, left_on='Country', right_on='Entity')
df_alignment = df_alignment[~df_alignment['Country'].isin(['World', 'Europe', 'European Union'])]

print("--- THEORETICAL INSIGHT ---")
print("Subsidizing EVs in coal-dominant countries yields marginal immediate benefits.")
print("This plots if EV adoption is actually happening where the grid is clean enough to help.")

print("\n--- RAW GRAPH DATA FOR EXTRACTION (Top 5 EV Adopters) ---")
top_countries = df_alignment.nlargest(5, 'Total_EVs')
for i, row in top_countries.iterrows():
    print(f"{row['Country']}: X (Grid) = {row['Carbon intensity']:.0f} g/kWh | Y (EVs) = {row['Total_EVs']:,.0f}")

plt.figure(figsize=(10, 6))
plt.scatter(df_alignment['Carbon intensity'], df_alignment['Total_EVs'], color='blue', alpha=0.6, s=100)
for i, row in top_countries.iterrows():
    plt.text(row['Carbon intensity'] + 10, row['Total_EVs'], row['Country'], fontsize=10, weight='bold')

plt.axvline(x=400, color='red', linestyle='--', label='Danger Zone (>400g CO2/kWh)')
plt.title(f'Climate Alignment: EV Adoption vs. Grid Cleanliness ({latest_ev_year})')
plt.xlabel('Grid Carbon Intensity (g CO2 per kWh)')
plt.ylabel('Total EVs on the Road (Stock)')
plt.yscale('log')
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 4: RENEWABLE READINESS
# ==========================================
print("\n" + "="*60)
print("INSIGHT 4: RENEWABLE READINESS FOR MASS EV ADOPTION")
print("="*60)

markets = ['China', 'United States', 'India', 'Germany', 'Norway']
year_start = 2013
year_end = df_energy['year'].max()

df_start = df_energy[(df_energy['country'].isin(markets)) & (df_energy['year'] == year_start)]
df_end = df_energy[(df_energy['country'].isin(markets)) & (df_energy['year'] == year_end)]

readiness_data = {}
for country in markets:
    try:
        start_pct = df_start[df_start['country'] == country]['renewables_electricity_share_pct'].values[0]
        end_pct = df_end[df_end['country'] == country]['renewables_electricity_share_pct'].values[0]
        readiness_data[country] = {'Start': start_pct, 'End': end_pct}
    except IndexError:
        pass

print("--- THEORETICAL INSIGHT ---")
print("If a country scales EVs without scaling renewable energy, they are artificially ")
print("masking emissions by moving them from the tailpipe to the power plant.")

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
for country, data in readiness_data.items():
    print(f"{country}: {year_start} = {data['Start']:.1f}% | {year_end} = {data['End']:.1f}%")

labels = list(readiness_data.keys())
start_values = [data['Start'] for data in readiness_data.values()]
end_values = [data['End'] for data in readiness_data.values()]
x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width/2, start_values, width, label=str(year_start), color='gray')
ax.bar(x + width/2, end_values, width, label=str(year_end), color='green')
ax.set_ylabel('Renewable Electricity Share (%)')
ax.set_title('Grid Transition: % of Electricity from Renewables')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
plt.grid(axis='y', linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 5: THE BATTERY ALLOCATION PARADOX
# ==========================================
print("\n" + "="*60)
print("INSIGHT 5: THE BATTERY ALLOCATION PARADOX")
print("="*60)

battery_budget_kwh = 1000  
suv_battery_size = 100     
sedan_battery_size = 60    

suvs_built = battery_budget_kwh / suv_battery_size
sedans_built = battery_budget_kwh / sedan_battery_size
us_grid = 0.360 
lifespan_km = 150000

lifetime_petrol_suv_co2 = (petrol_suv_co2 * lifespan_km) + petrol_mfg_co2
lifetime_ev_suv_co2 = (ev_suv_kwh * us_grid * lifespan_km) + ev_mfg_co2
suv_co2_saved = lifetime_petrol_suv_co2 - lifetime_ev_suv_co2

lifetime_petrol_sedan_co2 = (petrol_car_co2 * lifespan_km) + petrol_mfg_co2
lifetime_ev_sedan_co2 = (ev_car_kwh * us_grid * lifespan_km) + ev_mfg_co2
sedan_co2_saved = lifetime_petrol_sedan_co2 - lifetime_ev_sedan_co2

total_co2_saved_suvs = suvs_built * suv_co2_saved
total_co2_saved_sedans = sedans_built * sedan_co2_saved

print("--- THEORETICAL INSIGHT ---")
print("Battery minerals are limited. Splitting a 1MWh battery into smaller EV sedans ")
print("decarbonizes more vehicles and saves vastly more CO2 than building massive EV SUVs.")

labels = [f'{suvs_built} EV SUVs', f'{sedans_built:.1f} EV Sedans']
savings = [total_co2_saved_suvs, total_co2_saved_sedans]

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
print(f"X-Axis Labels: {labels}")
print(f"Y-Axis Values (kg CO2 Saved): {savings}")

plt.figure(figsize=(8, 5))
plt.bar(labels, savings, color=['#ff9999', '#66b3ff'])
plt.title('Total CO2 Saved per 1 MWh of Battery Capacity')
plt.ylabel('Lifetime CO2 Saved (kg)')
plt.grid(axis='y', linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 6: THE ECONOMIC PRIVILEGE OF EVS
# ==========================================
print("\n" + "="*60)
print("INSIGHT 6: THE GDP & EV MISMATCH (ECONOMIC PRIVILEGE)")
print("="*60)

latest_co2_year = df_co2[df_co2['gdp'].notna()]['year'].max()
df_co2_latest = df_co2[df_co2['year'] == latest_co2_year].copy()
df_co2_latest['gdp_per_capita'] = df_co2_latest['gdp'] / df_co2_latest['population']

# Merge ensuring we capture mapped names
df_econ = pd.merge(ev_stock_by_country, df_co2_latest, left_on='Country', right_on='country')
df_econ = df_econ[~df_econ['Country'].isin(['World', 'Europe', 'European Union', 'High-income countries'])]
df_econ_clean = df_econ.dropna(subset=['gdp_per_capita', 'Total_EVs', 'co2'])

top_20_percent_wealth = df_econ_clean['gdp_per_capita'].quantile(0.80)
wealthy_evs = df_econ_clean[df_econ_clean['gdp_per_capita'] >= top_20_percent_wealth]['Total_EVs'].sum()
total_global_evs = df_econ_clean['Total_EVs'].sum()
wealthy_share = (wealthy_evs / total_global_evs) * 100

print("--- THEORETICAL INSIGHT ---")
print("Global sustainability cannot be achieved if EVs remain a luxury product.")
print("The Global South has high CO2 (large bubbles) but low EV penetration due to GDP constraints.")

print("\n--- RAW GRAPH DATA FOR EXTRACTION (Top 5 Wealthiest Adapters) ---")
top_adopters = df_econ_clean.nlargest(5, 'Total_EVs')
for i, row in top_adopters.iterrows():
    print(f"{row['Country']}: GDP/Capita=${row['gdp_per_capita']:,.0f} | EVs={row['Total_EVs']:,.0f} | CO2={row['co2']:.1f}")

plt.figure(figsize=(10, 6))
x = df_econ_clean['gdp_per_capita']
y = df_econ_clean['Total_EVs']
bubble_size = df_econ_clean['co2'] / df_econ_clean['co2'].max() * 2000

plt.scatter(x, y, s=bubble_size, alpha=0.5, color='purple', edgecolors='black')
for i, row in top_adopters.iterrows():
    plt.text(row['gdp_per_capita'], row['Total_EVs'], row['Country'], fontsize=9, weight='bold')

plt.title('Global EV Adoption vs National Wealth (Bubble Size = Total CO2)')
plt.xlabel('GDP per Capita ($)')
plt.ylabel('Total EVs on the Road (Stock)')
plt.xscale('log')
plt.yscale('log')
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 7: THE GRID TIPPING POINT
# ==========================================
print("\n" + "="*60)
print("INSIGHT 7: THE GRID TIPPING POINT (EV vs PETROL vs DIESEL)")
print("="*60)

tipping_point_petrol = petrol_running_co2 / ev_kwh_per_km
tipping_point_diesel = diesel_running_co2 / ev_kwh_per_km

print("--- THEORETICAL INSIGHT ---")
print("There is a mathematical limit. If a grid is exceptionally dirty, an EV becomes ")
print("the worst option. This plots exactly where that line is.")

grid_range = np.linspace(0, 1000, 100)
ev_emissions_range = ev_kwh_per_km * (grid_range / 1000)

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
print(f"Petrol Constant Y: {petrol_running_co2:.3f} kg CO2/km")
print(f"Diesel Constant Y: {diesel_running_co2:.3f} kg CO2/km")
print(f"Tipping Point (EV > Diesel): {tipping_point_diesel*1000:.0f} gCO2/kWh")
print(f"Tipping Point (EV > Petrol): {tipping_point_petrol*1000:.0f} gCO2/kWh")

plt.figure(figsize=(10, 6))
plt.plot(grid_range, ev_emissions_range, label='EV Running Emissions', color='green', linewidth=3)
plt.axhline(y=petrol_running_co2, color='red', linestyle='-', label='Avg Petrol Emissions', linewidth=2)
plt.axhline(y=diesel_running_co2, color='orange', linestyle='--', label='Avg Diesel Emissions', linewidth=2)
plt.axvline(x=tipping_point_diesel*1000, color='gray', linestyle=':', alpha=0.7)
plt.axvline(x=tipping_point_petrol*1000, color='gray', linestyle=':', alpha=0.7)

plt.title('The Grid Tipping Point: EV vs Petrol vs Diesel')
plt.xlabel('Grid Carbon Intensity (grams CO2 per kWh)')
plt.ylabel('Running Emissions (kg CO2 per km)')
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 8: THE CARBON DEBT SPIKE
# ==========================================
print("\n" + "="*60)
print("INSIGHT 8: THE CARBON DEBT SPIKE (SHORT-TERM IMPACT)")
print("="*60)

fleet_size = 1000000 
annual_km = 15000     
test_grid_intensity = 0.450 
ev_running = ev_kwh_per_km * test_grid_intensity
years = np.arange(0, 6)

fleet_petrol_emissions = (petrol_mfg_co2 * fleet_size) + (petrol_running_co2 * annual_km * fleet_size * years)
fleet_ev_emissions = (ev_mfg_co2 * fleet_size) + (ev_running * annual_km * fleet_size * years)
net_emissions_added = fleet_ev_emissions - fleet_petrol_emissions
net_mt_co2 = net_emissions_added / 1e9 

print("--- THEORETICAL INSIGHT ---")
print("Rapid EV adoption causes an immediate global emissions SPIKE in Year 0 due to battery manufacturing.")
print("Policy targets must account for this delay in actual carbon reduction.")

print("\n--- RAW GRAPH DATA FOR EXTRACTION ---")
print("Net CO2 difference (Million Tonnes) if 1 Million EVs replace Petrol:")
for yr, val in zip(years, net_mt_co2):
    print(f"Year {yr}: {val:+.2f} Million Tonnes")

plt.figure(figsize=(10, 6))
colors = ['red' if val > 0 else 'green' for val in net_mt_co2]
plt.bar(years, net_mt_co2, color=colors)
plt.axhline(0, color='black', linewidth=1.5)
plt.title('The Carbon Debt Spike: Net CO2 Impact of 1 Million New EVs')
plt.xlabel('Years on the Road')
plt.ylabel('Net CO2 Difference (Million Tonnes)')

for i, v in enumerate(net_mt_co2):
    plt.text(i, v + (0.1 if v > 0 else -0.3), f"{v:+.1f} MT", ha='center', fontweight='bold')

plt.grid(axis='y', linestyle=':', alpha=0.7)
plt.show()


# ==========================================
# ANALYSIS 9: THE URBANIZATION CATALYST
# ==========================================
print("\n" + "="*60)
print("INSIGHT 9: THE URBANIZATION CATALYST (EV PENETRATION)")
print("="*60)

print("Loading World Bank demographic data...")
df_wb_raw = pd.read_excel("World Bank Climate & Energy Data.xls", sheet_name="Data", header=None)

# Dynamically find the row that contains our actual headers
header_idx = df_wb_raw[df_wb_raw.eq('Indicator Name').any(axis=1)].index[0]
df_wb = df_wb_raw.copy()
df_wb.columns = df_wb.iloc[header_idx]
df_wb = df_wb.iloc[header_idx + 1:].reset_index(drop=True)

df_urban = df_wb[df_wb['Indicator Name'] == 'Urban population (% of total population)']

recent_urban_year = None
years_to_check = [col for col in df_urban.columns if str(col).startswith('20')]
for year in sorted(years_to_check, reverse=True):
    if df_urban[year].notna().any():
        recent_urban_year = year
        break

df_urban_clean = df_urban[['Country Name', recent_urban_year]].copy()
df_urban_clean.rename(columns={'Country Name': 'Country', recent_urban_year: 'Urban_Pct'}, inplace=True)

df_insight9 = pd.merge(ev_stock_by_country, df_co2_latest[['country', 'population']], left_on='Country', right_on='country')
df_insight9 = pd.merge(df_insight9, df_urban_clean, on='Country')
df_insight9['EVs_per_1000'] = (df_insight9['Total_EVs'] / df_insight9['population']) * 1000
df_insight9 = df_insight9[~df_insight9['Country'].isin(['World', 'Europe', 'European Union', 'High-income countries'])]
df_insight9 = df_insight9.dropna(subset=['Urban_Pct', 'EVs_per_1000'])

print("--- THEORETICAL INSIGHT ---")
print("Electric vehicles are highly efficient in stop-and-go city traffic and eliminate ")
print("local air pollution. EV penetration (EVs per 1000 people) is exponentially higher ")
print("in highly urbanized nations, revealing that city density is a massive catalyst for adoption.")

print("\n--- RAW GRAPH DATA FOR EXTRACTION (Top 5 EV Penetration Rates) ---")
top_penetration = df_insight9.nlargest(5, 'EVs_per_1000')
for i, row in top_penetration.iterrows():
    print(f"{row['Country']}: Urbanization = {row['Urban_Pct']:.1f}% | EVs per 1000 people = {row['EVs_per_1000']:.1f}")

plt.figure(figsize=(10, 6))
plt.scatter(df_insight9['Urban_Pct'], df_insight9['EVs_per_1000'], color='teal', alpha=0.7, s=80, edgecolors='black')

for i, row in top_penetration.iterrows():
    plt.text(row['Urban_Pct'] - 1, row['EVs_per_1000'] + (row['EVs_per_1000']*0.1), row['Country'], fontsize=9, weight='bold', ha='right')

plt.title('The Urbanization Catalyst: City Density vs EV Penetration')
plt.xlabel('Urban Population (% of Total Population)')
plt.ylabel('EV Penetration (EVs per 1,000 People)')
plt.yscale('log') 
plt.grid(True, linestyle=':', alpha=0.7)
plt.show()