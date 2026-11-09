"""Clean and aggregate the raw data into the summary tables the dashboard reads.

Outputs:
  summary CSVs          one CSV per dashboard table
  data.js                the same tables bundled for index.html (so it also opens from disk)

Headline KPIs compare the latest 3 months (Aug-Oct 2026) with the prior 3 months (May-Jul 2026).
Run from the repository root:  python build_metrics.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent  # all files live in the repository root
RAW = ROOT
OUT = ROOT
CUR = ["2026-08", "2026-09", "2026-10"]
PRV = ["2026-05", "2026-06", "2026-07"]

# ---------- Logistics ----------
s=pd.read_csv(RAW / "logistics_shipments.csv"); f=pd.read_csv(RAW / "logistics_fleet.csv")
def lagg(d):
    return pd.Series(dict(shipments=len(d), on_time_pct=d.on_time.mean()*100,
        freight_cost=d.freight_cost.sum(), cost_per_mile=d.freight_cost.sum()/d.miles.sum(),
        avg_transit_days=d.transit_days.mean(), damage_rate=d.damaged.mean()*100))
lm=s.groupby("month").apply(lagg).reset_index()
fm=f.groupby("month").agg(fleet_utilization=("utilization","mean"),avg_mpg=("mpg","mean"),maintenance_cost=("maintenance_cost","sum")).reset_index()
fm["fleet_utilization"]*=100
lm=lm.merge(fm)
lm.round({"on_time_pct":1,"freight_cost":0,"cost_per_mile":2,"avg_transit_days":2,"damage_rate":2,"fleet_utilization":1,"avg_mpg":2,"maintenance_cost":0}).to_csv(OUT / "log_monthly.csv",index=False)
c=lagg(s[s.month.isin(CUR)]); p=lagg(s[s.month.isin(PRV)])
fc=f[f.month.isin(CUR)].utilization.mean()*100; fp=f[f.month.isin(PRV)].utilization.mean()*100
k=dict(window="Aug–Oct 2026",compare="May–Jul 2026",
  shipments=int(c.shipments),shipments_chg_pct=round((c.shipments/p.shipments-1)*100,1),
  on_time_pct=round(c.on_time_pct,1),on_time_chg_pts=round(c.on_time_pct-p.on_time_pct,1),
  cost_per_mile=round(c.cost_per_mile,2),cost_per_mile_chg_pct=round((c.cost_per_mile/p.cost_per_mile-1)*100,1),
  freight_cost=round(c.freight_cost),freight_cost_chg_pct=round((c.freight_cost/p.freight_cost-1)*100,1),
  fleet_utilization=round(fc,1),fleet_utilization_chg_pts=round(fc-fp,1),
  avg_transit_days=round(c.avg_transit_days,2),avg_transit_chg=round(c.avg_transit_days-p.avg_transit_days,2),
  otd_target=95.0)
pd.DataFrame([k]).to_csv(OUT / "log_kpis.csv",index=False)
car=s.groupby("carrier").apply(lambda d: pd.Series(dict(shipments=len(d),on_time_pct=d.on_time.mean()*100,
   cost_per_mile=d.freight_cost.sum()/d.miles.sum(),damage_rate=d.damaged.mean()*100,
   avg_days_late=d.loc[d.on_time==0,"days_late"].mean()))).reset_index().sort_values("on_time_pct",ascending=False)
car.round(2).to_csv(OUT / "log_carriers.csv",index=False)
ln=s.groupby(["destination","miles"]).apply(lambda d: pd.Series(dict(shipments=len(d),freight_cost=d.freight_cost.sum(),
   on_time_pct=d.on_time.mean()*100,avg_transit_days=d.transit_days.mean()))).reset_index()
ln["lane"]="Tulsa → "+ln.destination; ln=ln.sort_values("shipments",ascending=False)
ln[["lane","miles","shipments","freight_cost","on_time_pct","avg_transit_days"]].round({"freight_cost":0,"on_time_pct":1,"avg_transit_days":1}).to_csv(OUT / "log_lanes.csv",index=False)
md=s.groupby("mode").agg(shipments=("shipment_id","count"),freight_cost=("freight_cost","sum"),miles=("miles","sum")).reset_index()
md["cost_per_mile"]=md.freight_cost/md.miles; md["share_pct"]=md.shipments/md.shipments.sum()*100
md.drop(columns="miles").round(2).sort_values("shipments",ascending=False).to_csv(OUT / "log_modes.csv",index=False)
for f,cols in [("log_carriers.csv",["shipments"]),("log_lanes.csv",["shipments","freight_cost"]),
               ("log_monthly.csv",["shipments","freight_cost","maintenance_cost"]),("log_modes.csv",["freight_cost"])]:
    d=pd.read_csv(OUT/f); d[cols]=d[cols].round().astype(int); d.to_csv(OUT/f,index=False)

# Bundle tables for the dashboard page
DATASETS = {"kpis": "log_kpis.csv", "monthly": "log_monthly.csv", "carriers": "log_carriers.csv", "lanes": "log_lanes.csv", "modes": "log_modes.csv"}
bundle = {k: (OUT / v).read_text() for k, v in DATASETS.items()}
(ROOT / "data.js").write_text("window.DASH_DATA = " + json.dumps(bundle, indent=1) + ";\n")
print("Processed tables written to", OUT)
