"""Generate the synthetic raw data for the Logistics & Transportation dashboard.

All records are randomly generated with a fixed seed so results are reproducible.
No real company, customer or employee data is used.

Run from the repository root:  python generate_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent  # CSVs are written next to this script
rng = np.random.default_rng(42)
months = pd.date_range("2025-11-01", "2026-10-01", freq="MS")

# ---------- 1. Logistics & Transportation ----------
lanes = [("Tulsa, OK","Dallas, TX",257),("Tulsa, OK","Kansas City, MO",248),("Tulsa, OK","Oklahoma City, OK",106),
         ("Tulsa, OK","Houston, TX",490),("Tulsa, OK","Denver, CO",680),("Tulsa, OK","Memphis, TN",400),
         ("Tulsa, OK","St. Louis, MO",395),("Tulsa, OK","Little Rock, AR",275),("Tulsa, OK","Wichita, KS",175),
         ("Tulsa, OK","Chicago, IL",690)]
carriers = {"Red River Freight":0.95,"Prairie Line Logistics":0.91,"Summit Carriers":0.88,"Heartland Express Co.":0.93,"Cimarron Transport":0.85}
modes = {"FTL":(2.45,0.45),"LTL":(3.60,0.35),"Intermodal":(1.85,0.20)}
rows=[]; sid=100000
for m_i,m in enumerate(months):
    seas = (1 + 0.14*np.cos((m.month-11)/12*2*np.pi))*(1+0.008*m_i)
    n = int(rng.normal(620,30)*seas)
    for _ in range(n):
        o,d,miles = lanes[rng.choice(len(lanes), p=[.17,.13,.14,.12,.06,.09,.09,.07,.08,.05])]
        car = rng.choice(list(carriers))
        mode = rng.choice(list(modes), p=[.5,.38,.12]) if miles>300 else rng.choice(["FTL","LTL"],p=[.45,.55])
        rpm = modes[mode][0]*rng.normal(1,0.08)*(1.06 if m.month in (11,12) else 1)
        cost = miles*rpm + (rng.normal(180,40) if mode=="LTL" else 0)
        weight = rng.normal(38000,5000) if mode!="LTL" else rng.normal(6500,2500)
        p_on = carriers[car] - (0.04 if m.month in (12,1) else 0) - (0.03 if miles>500 else 0) + 0.004*m_i
        on = rng.random()<min(p_on,0.99)
        delay = 0 if on else max(1,int(rng.exponential(1.4))+1)
        transit = max(1,round(miles/450+rng.normal(0.6,0.3)))+delay
        rows.append(dict(shipment_id=f"SH{sid}",month=m.strftime("%Y-%m"),origin=o,destination=d,miles=miles,
            carrier=car,mode=mode,weight_lbs=round(max(weight,500)),freight_cost=round(cost,2),
            on_time=int(on),days_late=delay,transit_days=transit,
            damaged=int(rng.random()<0.012)))
        sid+=1
ship=pd.DataFrame(rows); ship.to_csv(RAW / "logistics_shipments.csv",index=False)

fleet=[]
for m_i,m in enumerate(months):
    seas = 1 + 0.12*np.cos((m.month-11)/12*2*np.pi)
    for t in range(1,41):
        util = np.clip(rng.normal(0.78*seas,0.07),0.4,0.98)
        mpg = rng.normal(6.6+0.01*m_i,0.25)
        fleet.append(dict(month=m.strftime("%Y-%m"),truck_id=f"TRK-{t:03d}",utilization=round(util,3),
            miles_driven=int(util*11000*rng.normal(1,0.05)),mpg=round(mpg,2),
            maintenance_cost=round(max(0,rng.gamma(2,450)),2)))
pd.DataFrame(fleet).to_csv(RAW / "logistics_fleet.csv",index=False)
print("Raw data written to", RAW)
