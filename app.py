"""KisanUrja Grid MVP - Flask + SQLite. Run: python app.py"""
import os, io, re, json, math, time, random, sqlite3, secrets, base64, hashlib, logging, urllib.request
from datetime import date, datetime, timedelta
from functools import wraps
import numpy as np
from PIL import Image
from flask import Flask, g, jsonify, request, send_from_directory
import ml
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 8*1024*1024
DB = os.environ.get("KU_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "kisanurja.db"))
TOKEN_DAYS = 7
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
HITS = {}
def limited(key, n=8, win=300):
    now = time.time(); h = [x for x in HITS.get(key, []) if now-x < win]; h.append(now); HITS[key] = h; return len(h) > n
@app.after_request
def headers(r):
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
        "Permissions-Policy": "camera=(self), microphone=(self)",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: blob: https:; media-src 'self' blob:; connect-src 'self'"})
    if request.path.startswith("/api/"): r.headers["Cache-Control"] = "no-store"
    return r
@app.errorhandler(413)
def big(_): return jsonify(error="File too large (max 8 MB)"), 413
@app.errorhandler(500)
def boom(e): logging.exception("server error"); return jsonify(error="Server error"), 500
@app.get("/healthz")
def healthz(): return jsonify(ok=1)
GRID_TARIFF, SOLAR_TARIFF, DIESEL, EF = 8.0, 3.5, 28.0, 0.82  # Rs/kWh, Rs/kWh, Rs/kWh, kgCO2/kWh
PLANT_KW = 60

# ---------------- DB ----------------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d: d.close()
def q(sql, a=(), one=False):
    c = db().execute(sql, a); r = c.fetchall(); db().commit()
    return (r[0] if r else None) if one else r

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, phone TEXT UNIQUE, name TEXT, pw TEXT, role TEXT,
 state TEXT, district TEXT, land REAL, crop TEXT, pump_kw REAL, solar_kw REAL, lang TEXT DEFAULT 'en', cluster INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY, user_id INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS readings(user_id INT, day TEXT, solar_kwh REAL, grid_kwh REAL, water_kl REAL, paid INT);
CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, day TEXT, user_id INT, kwh REAL, amount REAL, ref TEXT);
CREATE TABLE IF NOT EXISTS otps(phone TEXT PRIMARY KEY, code TEXT, exp REAL, tries INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY, cat TEXT, title TEXT, summ TEXT, body TEXT, img TEXT, mins INT, featured INT, cta TEXT);
CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY, user_id INT, ts TEXT, result TEXT);
CREATE INDEX IF NOT EXISTS ix_r ON readings(user_id, day);
CREATE INDEX IF NOT EXISTS ix_l ON ledger(day);
"""
NAMES = ["Ramesh Yadav","Sunita Devi","Harpreet Singh","Lakshmi Bai","Mohan Lal","Geeta Kumari","Balwinder Singh","Savitri Patel","Kishan Rao","Anita Meena","Jagdish Choudhary"]
def init():
    c = sqlite3.connect(DB); c.executescript(SCHEMA)
    try: c.execute("ALTER TABLE tokens ADD COLUMN created TEXT")
    except sqlite3.OperationalError: pass
    if not c.execute("SELECT 1 FROM users").fetchone():
        rnd = random.Random(7)
        rows = [("9999900001","Demo Farmer","farmer","Punjab","Sangrur",4.0,"Paddy",7.5,5.0),
                ("9999900002","DISCOM Officer","officer","Punjab","Sangrur",0,"",0,0)]
        for i, n in enumerate(NAMES):
            rows.append((f"98765000{i+10}", n, "farmer", "Punjab", "Sangrur", round(rnd.uniform(1.5,8),1),
                         rnd.choice(["Paddy","Wheat","Cotton","Maize"]), rnd.choice([3.7,5.6,7.5]), rnd.choice([3,5,5,7.5])))
        for p, n, role, st, di, land, crop, pk, sk in rows:
            c.execute("INSERT INTO users(phone,name,pw,role,state,district,land,crop,pump_kw,solar_kw) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (p, n, generate_password_hash("demo123"), role, st, di, land, crop, pk, sk))
        for uid, in c.execute("SELECT id FROM users WHERE role='farmer'").fetchall():
            for d in range(90):
                day = (date.today()-timedelta(days=89-d)).isoformat()
                sol = max(0, rnd.gauss(18,5)) * (1+d/300); grid = max(0, rnd.gauss(8,3)) * (1-d/250)
                c.execute("INSERT INTO readings VALUES(?,?,?,?,?,?)", (uid, day, round(sol,1), round(grid,1),
                          round(max(5, rnd.gauss(45,12)*(1-d/400)),1), 1 if rnd.random() < .93 else 0))
        c.commit()
    if not c.execute("SELECT 1 FROM articles").fetchone():
        from content import ARTICLES
        for a in ARTICLES: c.execute("INSERT INTO articles(cat,title,summ,body,img,mins,featured,cta) VALUES(?,?,?,?,?,?,?,?)", (a[0], json.dumps(a[1]), json.dumps(a[2]), json.dumps(a[3]), a[4], a[5], a[6], a[7]))
    c.commit(); c.close()

# ---------------- auth ----------------
def auth(role=None):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            t = hashlib.sha256(request.headers.get("Authorization", "").replace("Bearer ", "").encode()).hexdigest()
            r = q("SELECT u.*, t.created FROM tokens t JOIN users u ON u.id=t.user_id WHERE t.token=?", (t,), one=True)
            if not r or datetime.fromisoformat(r["created"] or "2000-01-01") < datetime.now()-timedelta(days=TOKEN_DAYS): return jsonify(error="auth"), 401
            if role and r["role"] != role: return jsonify(error="forbidden"), 403
            g.user = r; return f(*a, **k)
        return w
    return deco
def pub(u): return {k: u[k] for k in ("id","phone","name","role","state","district","land","crop","pump_kw","solar_kw","lang")}
@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    if limited("reg"+request.remote_addr): return jsonify(error="Too many attempts, try later"), 429
    num = lambda k, lo, hi, df: max(lo, min(hi, float(d.get(k) or df)))
    if not re.fullmatch(r"\d{10}", str(d.get("phone",""))) or len(d.get("password","")) < 6 or not str(d.get("name","")).strip(): return jsonify(error="Name, 10-digit phone and 6+ char password required"), 400
    d["name"] = str(d["name"]).strip()[:60]; d["state"] = str(d.get("state") or "Punjab")[:40]; d["district"] = str(d.get("district",""))[:40]
    if d.get("crop") not in ("Paddy","Wheat","Cotton","Maize"): d["crop"] = "Wheat"
    d["land"], d["pump_kw"], d["solar_kw"] = num("land",.1,500,2), num("pump_kw",.5,50,5), num("solar_kw",0,100,0)
    if q("SELECT 1 FROM users WHERE phone=?", (d["phone"],), one=True): return jsonify(error="Phone already registered"), 409
    q("INSERT INTO users(phone,name,pw,role,state,district,land,crop,pump_kw,solar_kw) VALUES(?,?,?,?,?,?,?,?,?,?)",
      (d["phone"], d["name"], generate_password_hash(d["password"]), "farmer", d.get("state","Punjab"), d.get("district",""),
       d["land"], d["crop"], d["pump_kw"], d["solar_kw"]))
    return login()
@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    if limited("log"+request.remote_addr+str(d.get("phone"))): return jsonify(error="Too many attempts, try again in 5 minutes"), 429
    u = q("SELECT * FROM users WHERE phone=?", (d.get("phone"),), one=True)
    if not u or not check_password_hash(u["pw"], d.get("password","")): return jsonify(error="Wrong phone or password"), 401
    t = secrets.token_hex(24); q("INSERT INTO tokens VALUES(?,?,?)", (hashlib.sha256(t.encode()).hexdigest(), u["id"], datetime.now().isoformat()))
    q("DELETE FROM tokens WHERE created < ?", ((datetime.now()-timedelta(days=TOKEN_DAYS)).isoformat(),)); return jsonify(token=t, user=pub(u))
@app.post("/api/otp/request")
def otp_req():
    ph = str((request.get_json(silent=True) or {}).get("phone", ""))
    if not re.fullmatch(r"\d{10}", ph): return jsonify(error="Enter 10-digit mobile number"), 400
    if limited("otp"+request.remote_addr+ph, 3, 300): return jsonify(error="Too many OTP requests"), 429
    code = f"{secrets.randbelow(10**6):06d}"
    q("INSERT OR REPLACE INTO otps VALUES(?,?,?,0)", (ph, hashlib.sha256(code.encode()).hexdigest(), time.time()+300))
    logging.info("OTP issued for %s***", ph[:4])  # TODO: send via SMS gateway (MSG91/Twilio)
    return jsonify(ok=1, dev_otp=code if os.environ.get("KU_DEV_OTP", "1") == "1" else None)
@app.post("/api/otp/verify")
def otp_verify():
    d = request.get_json(silent=True) or {}; o = q("SELECT * FROM otps WHERE phone=?", (d.get("phone"),), one=True)
    if not o or o["exp"] < time.time() or o["tries"] >= 5: return jsonify(error="OTP expired – request a new one"), 401
    q("UPDATE otps SET tries=tries+1 WHERE phone=?", (o["phone"],))
    if hashlib.sha256(str(d.get("code","")).encode()).hexdigest() != o["code"]: return jsonify(error="Wrong OTP"), 401
    u = q("SELECT * FROM users WHERE phone=?", (o["phone"],), one=True)
    if not u: return jsonify(error="No account for this number – please register"), 404
    q("DELETE FROM otps WHERE phone=?", (o["phone"],)); t = secrets.token_hex(24)
    q("INSERT INTO tokens VALUES(?,?,?)", (hashlib.sha256(t.encode()).hexdigest(), u["id"], datetime.now().isoformat())); return jsonify(token=t, user=pub(u))
@app.post("/api/logout")
@auth()
def logout(): q("DELETE FROM tokens WHERE user_id=?", (g.user["id"],)); logging.info("logout %s", g.user["id"]); return jsonify(ok=1)
@app.get("/api/me")
@auth()
def me(): return jsonify(pub(g.user))

# ---------------- ML / engines ----------------
def weather(day):
    """Deterministic synthetic forecast (swap for IMD / Open-Meteo in production)."""
    r = random.Random(day); cloud = r.choice([.05,.1,.2,.3,.5,.8]); rain = cloud > .6 and r.random() < .6
    return {"cloud": cloud, "rain_mm": round(r.uniform(4,18),1) if rain else 0.0, "temp": round(r.uniform(24,38),1)}
def solar_curve(day, kw=PLANT_KW):
    w = weather(day); cf = ml.solar_cf(w["cloud"], w["temp"])  # trained GradientBoosting forecaster
    return [round(float(kw*c), 2) if 6 <= h <= 18 else 0.0 for h, c in enumerate(cf)], w  # no output at night
def demand_profile(u, day):
    """Pump kW per hour. Farmers prefer 6-11 & 15-18 irrigation windows scaled by land."""
    r = random.Random(f"{u['id']}{day}"); hrs = max(1.5, min(9, u["land"]*1.1)); out = [0.0]*24
    pref = [6,7,8,9,10,15,16,17,5,11,14,18,19,4]
    for h in pref[:int(round(hrs))]: out[h] = round(u["pump_kw"]*r.uniform(.8,1), 2)
    return out
def fair_share(supply, demands, weights):
    """Weighted max-min fairness (water-filling). Nobody gets more than asked; scarce supply split by land weight."""
    alloc = [0.0]*len(demands); act = [i for i, d in enumerate(demands) if d > 0]; rem = supply
    while act and rem > 1e-9:
        tw = sum(weights[i] for i in act); done = []
        for i in act:
            s = rem*weights[i]/tw
            if demands[i]-alloc[i] <= s + 1e-9: done.append(i)
        if not done:
            for i in act: alloc[i] += rem*weights[i]/tw
            break
        for i in done: rem -= demands[i]-alloc[i]; alloc[i] = demands[i]; act.remove(i)
    return alloc
def cluster_sim(cluster, day):
    us = q("SELECT * FROM users WHERE role='farmer' AND cluster=? ORDER BY id", (cluster,))
    supply, w = solar_curve(day); D = [demand_profile(u, day) for u in us]; wt = [u["land"] for u in us]
    per = [{"id": u["id"], "name": u["name"], "land": u["land"], "demand": 0, "solar": 0, "grid": 0} for u in us]; hourly = []
    for h in range(24):
        dem = [D[i][h] for i in range(len(us))]; al = fair_share(supply[h], dem, wt)
        for i in range(len(us)): per[i]["demand"] += dem[i]; per[i]["solar"] += al[i]; per[i]["grid"] += dem[i]-al[i]
        hourly.append({"h": h, "supply": supply[h], "demand": round(sum(dem),2), "served": round(sum(al),2), "grid": round(sum(dem)-sum(al),2)})
    for p in per:
        for k in ("demand","solar","grid"): p[k] = round(p[k],2)
        p["cost"] = round(p["solar"]*SOLAR_TARIFF + p["grid"]*GRID_TARIFF, 1); p["baseline"] = round(p["demand"]*DIESEL*.5+p["demand"]*GRID_TARIFF*.5, 1)
    ts = sum(p["solar"] for p in per); td = sum(p["demand"] for p in per)
    return {"day": day, "weather": w, "hourly": hourly, "members": per, "plant_kw": PLANT_KW,
            "totals": {"demand": round(td,1), "solar_served": round(ts,1), "grid": round(td-ts,1), "utilisation": round(100*ts/max(1,sum(supply)),1),
                       "saved_inr": round(sum(p["baseline"]-p["cost"] for p in per)), "co2_kg": round(ts*EF,1),
                       "fairness": round(jain([p["solar"]/max(.01,p["demand"]) for p in per if p["demand"]]),3)}}
def jain(x): x = np.array(x); return float(x.sum()**2/(len(x)*(x**2).sum())) if len(x) and x.sum() else 1.0

@app.get("/api/solar/simulate")
@auth()
def solar_sim(): return jsonify(cluster_sim(g.user["cluster"], request.args.get("day", date.today().isoformat())))
@app.post("/api/solar/settle")
@auth()
def settle():
    day = (request.json or {}).get("day", date.today().isoformat()); s = cluster_sim(g.user["cluster"], day)
    q("DELETE FROM ledger WHERE day=?", (day,))
    for m in s["members"]:
        q("INSERT INTO ledger(day,user_id,kwh,amount,ref) VALUES(?,?,?,?,?)", (day, m["id"], m["solar"], round(m["solar"]*SOLAR_TARIFF,1), "UPI" + secrets.token_hex(5).upper()))
    return ledger()
@app.get("/api/solar/ledger")
@auth()
def ledger():
    r = q("SELECT l.*, u.name FROM ledger l JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 40")
    return jsonify([dict(x) for x in r])

def readings(uid, days=30):
    return q("SELECT * FROM readings WHERE user_id=? ORDER BY day DESC LIMIT ?", (uid, days))[::-1]
def stress_model(u, rows):
    """Groundwater stress: pumped water vs block recharge allowance (rule + logistic)."""
    kl = np.mean([r["water_kl"] for r in rows]) if rows else 0; per_acre = kl/max(.5, u["land"])
    crop_need = {"Paddy": 14, "Wheat": 7, "Cotton": 9, "Maize": 8}.get(u["crop"], 9)
    ratio = per_acre/crop_need; score = 1/(1+math.exp(-4*(ratio-1)))
    blk = "Over-exploited" if u["state"] in ("Punjab","Haryana") else "Semi-critical"
    return {"kl_day": round(kl,1), "per_acre": round(per_acre,1), "crop_need": crop_need, "ratio": round(ratio,2), "stress": round(score*100), "block": blk}
def anomalies(rows):
    v = np.array([r["solar_kwh"] for r in rows]); 
    if len(v) < 8: return []
    mu, sd = v.mean(), v.std() or 1; return [{"day": r["day"], "z": round((r["solar_kwh"]-mu)/sd,1)} for r in rows if (r["solar_kwh"]-mu)/sd < -1.8]
def credit(u):
    rows = readings(u["id"], 90); n = max(1, len(rows))
    f = {"punctuality": sum(r["paid"] for r in rows)/n,
         "solar_use": min(1, sum(r["solar_kwh"] for r in rows)/max(1, sum(r["solar_kwh"]+r["grid_kwh"] for r in rows))*1.15),
         "water_eff": max(0, min(1, 1.35-stress_model(u, rows[-30:])["ratio"]*.5)),
         "tenure": min(1, n/90), "schemes": min(1, len(match_schemes(u, True))/6)}
    W = {"punctuality": 30, "solar_use": 25, "water_eff": 20, "tenure": 10, "schemes": 15}
    LBL = {"punctuality": ("Bill payment punctuality","बिल भुगतान समय पर"), "solar_use": ("Solar share of energy","सौर ऊर्जा का हिस्सा"),
           "water_eff": ("Water-use efficiency","जल उपयोग दक्षता"), "tenure": ("Data history length","डेटा इतिहास"), "schemes": ("Scheme participation","योजना भागीदारी")}
    contrib = [{"key": k, "en": LBL[k][0], "hi": LBL[k][1], "value": round(f[k],2), "points": round(W[k]*f[k],1), "max": W[k]} for k in W]
    pd_, imp = ml.default_prob(f); sc = int(max(300, min(900, 900-1100*pd_)))
    for c in contrib: c["impact"] = imp[c["key"]]
    return {"pd": round(pd_*100, 1), "model": "Logistic regression (AUC %s)" % ml.METRICS["credit_auc"], "score": sc, "band": "Excellent" if sc > 780 else "Good" if sc > 680 else "Fair" if sc > 560 else "Building", "factors": contrib,
            "eligible_limit": int(25000*(sc-300)/10), "note": "Explainable weighted model; lenders see every factor. Seasonal harvest lumpiness is not penalised."}
def carbon(u):
    rows = readings(u["id"], 90); sol = sum(r["solar_kwh"] for r in rows)
    diesel_l = sol*0.30; co2 = sol*EF/1000
    water = max(0, (14 if u["crop"]=="Paddy" else 8)*u["land"]*90 - sum(r["water_kl"] for r in rows))
    return {"solar_kwh": round(sol), "diesel_l": round(diesel_l), "co2_t": round(co2,2), "water_saved_kl": round(water),
            "credit_inr": round(co2*900), "score": min(100, int(30+co2*12+min(30, water/200)))}

SCHEMES = [
 dict(id="kusum", n=("PM-KUSUM","पीएम-कुसुम"), d=("Subsidised solar pumps and feeder solarisation; up to 30% central + 30% state support.","सब्सिडी वाले सौर पंप और फीडर सोलराइजेशन; 30% केंद्र + 30% राज्य सहायता।"), img="solar,farm,india", url="https://pmkusum.mnre.gov.in", cat="Energy"),
 dict(id="surya", n=("PM Surya Ghar","पीएम सूर्य घर"), d=("Rooftop solar for homes incl. farm homesteads, subsidy up to ₹78,000.","घरों/फार्महाउस के लिए रूफटॉप सोलर, ₹78,000 तक सब्सिडी।"), img="rooftop,solar,village", url="https://pmsuryaghar.gov.in", cat="Energy"),
 dict(id="kisan", n=("PM-KISAN","पीएम-किसान"), d=("₹6,000 a year income support in three instalments for landholding families.","भूमिधारक परिवारों को ₹6,000 वार्षिक आय सहायता।"), img="indian,farmer,field", url="https://pmkisan.gov.in", cat="Income"),
 dict(id="kcc", n=("Kisan Credit Card","किसान क्रेडिट कार्ड"), d=("Low-interest crop loans up to ₹3 lakh with interest subvention.","₹3 लाख तक का कम ब्याज फसल ऋण।"), img="india,farmer,money", url="https://www.nabard.org", cat="Credit"),
 dict(id="pmfby", n=("PM Fasal Bima Yojana","पीएम फसल बीमा योजना"), d=("Crop insurance against drought, flood, pests at 1.5–5% premium.","सूखा, बाढ़, कीट के विरुद्ध 1.5–5% प्रीमियम पर फसल बीमा।"), img="crop,damage,field", url="https://pmfby.gov.in", cat="Insurance"),
 dict(id="pmksy", n=("PMKSY – Per Drop More Crop","पीएमकेएसवाई – प्रति बूंद अधिक फसल"), d=("Up to 55% subsidy on drip and sprinkler irrigation.","ड्रिप व स्प्रिंकलर पर 55% तक सब्सिडी।"), img="drip,irrigation,farm", url="https://pmksy.gov.in", cat="Water"),
 dict(id="shc", n=("Soil Health Card","मृदा स्वास्थ्य कार्ड"), d=("Free soil testing with crop-wise fertiliser advice.","निःशुल्क मिट्टी जांच और उर्वरक सलाह।"), img="soil,farmer,india", url="https://soilhealth.dac.gov.in", cat="Soil"),
 dict(id="enam", n=("e-NAM","ई-नाम"), d=("National online mandi to sell produce at better prices.","बेहतर दाम पर उपज बेचने हेतु राष्ट्रीय ऑनलाइन मंडी।"), img="mandi,market,vegetables,india", url="https://enam.gov.in", cat="Market"),
]
def match_schemes(u, ids_only=False):
    out = []
    for s in SCHEMES:
        sc = 60; why = []
        if s["id"] == "kusum": sc = 95 if u["solar_kw"] < 1 else 70; why = ["Needs irrigation pump", "No solar yet" if u["solar_kw"] < 1 else "Already solar – feeder/Component C tracking"]
        if s["id"] == "surya": sc = 65 if u["solar_kw"] < 1 else 40
        if s["id"] == "kisan": sc = 90 if u["land"] <= 5 else 70; why = ["Landholding family"]
        if s["id"] == "kcc": sc = 88; why = ["Crop loans need no collateral to ₹1.6 lakh"]
        if s["id"] == "pmfby": sc = 85; why = [f"{u['crop']} is a notified crop"]
        if s["id"] == "pmksy": sc = 92 if u["crop"] in ("Paddy","Cotton","Maize") or u["state"] in ("Punjab","Haryana") else 70; why = ["Groundwater block is stressed"] if u["state"] in ("Punjab","Haryana") else []
        if s["id"] == "shc": sc = 80
        if s["id"] == "enam": sc = 72
        out.append({**s, "n": {"en": s["n"][0], "hi": s["n"][1]}, "d": {"en": s["d"][0], "hi": s["d"][1]}, "match": sc, "why": why})
    out.sort(key=lambda x: -x["match"]); return [o for o in out if o["match"] >= 70] if ids_only else out

@app.get("/api/dashboard")
@auth()
def dashboard():
    u = g.user; rows = readings(u["id"], 30); sol, grid = sum(r["solar_kwh"] for r in rows), sum(r["grid_kwh"] for r in rows)
    sm = stress_model(u, rows); cr = credit(u); cb = carbon(u); today = date.today().isoformat(); sc, w = solar_curve(today)
    return jsonify(series=[dict(day=r["day"], solar=r["solar_kwh"], grid=r["grid_kwh"], water=r["water_kl"]) for r in rows],
        kpi={"solar_kwh": round(sol), "grid_kwh": round(grid), "saved_inr": round(sol*(DIESEL*.5+GRID_TARIFF*.5-SOLAR_TARIFF)), "water_kl": round(sum(r["water_kl"] for r in rows))},
        stress=sm, credit=cr["score"], band=cr["band"], carbon=cb, weather=w, today_solar=round(sum(sc)), tip=advisor(u, today))
def advisor(u, day):
    sc, w = solar_curve(day); tm = (date.fromisoformat(day)+timedelta(days=1)).isoformat(); w2 = weather(tm)
    rows = readings(u["id"], 7); wet = sum(r["water_kl"] for r in rows)/max(1,len(rows))
    best = sorted(range(24), key=lambda h: -sc[h])[:4]
    if w["rain_mm"] > 5: a = ("WAIT","Rain expected today (%s mm) – skip irrigation." % w["rain_mm"],"आज बारिश (%s मिमी) – सिंचाई रोकें।" % w["rain_mm"])
    elif w2["rain_mm"] > 8: a = ("WAIT","Rain forecast tomorrow – irrigate lightly today.","कल बारिश – आज हल्की सिंचाई करें।")
    else: a = ("WATER","Irrigate today at %s – peak solar, no grid needed." % ", ".join(f"{h}:00" for h in sorted(best)[:2]),"आज %s बजे सिंचाई करें – अधिकतम सौर ऊर्जा।" % ", ".join(str(h) for h in sorted(best)[:2]))
    return {"action": a[0], "en": a[1], "hi": a[2], "best_hours": sorted(best), "moisture": round(max(18, 62-wet*.4+(8 if w["rain_mm"] else 0))), "weather": w, "tomorrow": w2}
@app.get("/api/water")
@auth()
def water():
    u = g.user; rows = readings(u["id"], 60)
    return jsonify(stress=stress_model(u, rows[-30:]), anomalies=anomalies(rows), series=[dict(day=r["day"], water=r["water_kl"], solar=r["solar_kwh"]) for r in rows], advisor=advisor(u, date.today().isoformat()))
@app.get("/api/schemes")
@auth()
def schemes(): return jsonify(match_schemes(g.user))
@app.get("/api/credit")
@auth()
def credit_ep(): return jsonify(credit(g.user))
@app.get("/api/carbon")
@auth()
def carbon_ep(): return jsonify(carbon(g.user))

@app.get("/api/officer/overview")
@auth("officer")
def officer():
    fs = q("SELECT * FROM users WHERE role='farmer'"); data = []
    for u in fs:
        rows = readings(u["id"], 30); sm = stress_model(u, rows); data.append({"name": u["name"], "district": u["district"], "crop": u["crop"], "land": u["land"], "stress": sm["stress"], "solar": round(sum(r["solar_kwh"] for r in rows)), "credit": credit(u)["score"]})
    return jsonify(farmers=data, sim=cluster_sim(1, date.today().isoformat())["totals"])

# ---------------- crop vision ----------------
DIAG = {
 "healthy": ("Healthy crop", "स्वस्थ फसल", "Leaves look healthy. Continue current irrigation; re-scan weekly.", "पत्तियां स्वस्थ हैं। वर्तमान सिंचाई जारी रखें; साप्ताहिक जांच करें।"),
 "yellow": ("Yellowing – nitrogen deficiency / water stress", "पीलापन – नाइट्रोजन की कमी / जल तनाव", "Check soil moisture first. If moisture is fine, apply urea ~25 kg/acre split dose; get a Soil Health Card test.", "पहले मिट्टी की नमी जांचें। नमी ठीक हो तो यूरिया ~25 किग्रा/एकड़ दो बार में दें; मृदा परीक्षण कराएं।"),
 "spot": ("Brown spots – possible leaf blight / fungal spot", "भूरे धब्बे – संभावित पत्ती झुलसा / फफूंद", "Remove worst leaves, avoid evening irrigation, consult KVK for fungicide (e.g. mancozeb) dosage.", "अधिक प्रभावित पत्ते हटाएं, शाम को सिंचाई न करें, फफूंदनाशक की मात्रा के लिए कृषि विज्ञान केंद्र से पूछें।"),
 "both": ("Severe stress – yellowing with lesions", "गंभीर तनाव – पीलापन व धब्बे", "Likely disease plus nutrient stress. Visit nearest KVK / call Kisan Call Centre 1800-180-1551 with this photo.", "रोग व पोषक तत्व तनाव की संभावना। किसान कॉल सेंटर 1800-180-1551 पर संपर्क करें।"),
 "none": ("No clear leaf detected", "पत्ती स्पष्ट नहीं दिखी", "Retake: fill the frame with one leaf, daylight, no shadow.", "दोबारा लें: एक पत्ती फ्रेम में रखें, दिन की रोशनी में, छाया न हो।")}
def analyse_image(img):
    im = img.convert("RGB").resize((224,224)); hsv = np.array(im.convert("HSV")).astype(int); h, s, v = hsv[...,0], hsv[...,1], hsv[...,2]
    green = (h>=48)&(h<=120)&(s>60)&(v>50); yellow = (h>=26)&(h<48)&(s>70)&(v>90); brown = (h>=5)&(h<30)&(s>60)&(v<150)&(v>25)
    tot = green.sum()+yellow.sum()+brown.sum(); cover = tot/h.size
    if cover < .08: key, conf = "none", .9; fr = dict(green=0,yellow=0,brown=0)
    else:
        fr = dict(green=green.sum()/tot, yellow=yellow.sum()/tot, brown=brown.sum()/tot)
        key = "both" if fr["yellow"]>.18 and fr["brown"]>.08 else "yellow" if fr["yellow"]>.18 else "spot" if fr["brown"]>.08 else "healthy"
        conf = round(min(.93, .6+abs(fr["green"]-.5)*.5),2)
    from scipy import ndimage
    _, nsp = ndimage.label(brown | (yellow & (s > 120))); spots = int(min(nsp, 99))
    d = DIAG[key]; health = int(round(100*(fr["green"]-.5*fr["yellow"]-fr["brown"])))
    return {"key": key, "en": d[0], "hi": d[1], "adv_en": d[2], "adv_hi": d[3], "confidence": conf, "health": max(0,min(100,health)),
            "cover": round(float(cover)*100), "spots": spots, "fractions": {k: round(float(x)*100) for k,x in fr.items()}, "engine": "colour-segmentation (HSV) – prototype"}
def claude_vision(raw, mime):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: return None
    body = json.dumps({"model": "claude-sonnet-4-6", "max_tokens": 300, "messages": [{"role":"user","content":[
        {"type":"image","source":{"type":"base64","media_type":mime,"data":base64.b64encode(raw).decode()}},
        {"type":"text","text":"Indian crop photo. In 3 short lines: crop, likely problem (or healthy), one action. Then the same in Hindi."}]}]}).encode()
    try:
        r = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        return json.load(urllib.request.urlopen(r, timeout=25))["content"][0]["text"]
    except Exception: return None
@app.post("/api/crop/analyze")
@auth()
def crop():
    f = request.files.get("image")
    if not f: return jsonify(error="no image"), 400
    raw = f.read()
    try: img = Image.open(io.BytesIO(raw))
    except Exception: return jsonify(error="bad image"), 400
    res = analyse_image(img); res["ai_note"] = claude_vision(raw, f.mimetype or "image/jpeg")
    q("INSERT INTO scans(user_id,ts,result) VALUES(?,?,?)", (g.user["id"], datetime.now().isoformat(), json.dumps(res))); return jsonify(res)
@app.get("/api/crop/history")
@auth()
def hist(): return jsonify([{**json.loads(r["result"]), "ts": r["ts"]} for r in q("SELECT * FROM scans WHERE user_id=? ORDER BY id DESC LIMIT 6", (g.user["id"],))])

@app.post("/api/chat")
@auth()
def chat():
    m = (request.json or {}).get("message","").lower(); u = g.user; tip = advisor(u, date.today().isoformat()); cr = credit(u)
    if any(k in m for k in ("water","pani","पानी","सिंचाई","irrigat")): en, hi = tip["en"], tip["hi"]
    elif any(k in m for k in ("loan","credit","लोन","ऋण","कर्ज")): en, hi = f"Your KisanUrja score is {cr['score']} ({cr['band']}). Indicative KCC limit ₹{cr['eligible_limit']:,}.", f"आपका स्कोर {cr['score']} है। अनुमानित KCC सीमा ₹{cr['eligible_limit']:,}।"
    elif any(k in m for k in ("scheme","yojana","योजना","subsid","kusum")): t = match_schemes(u)[0]; en, hi = f"Best match: {t['n']['en']} ({t['match']}%). {t['d']['en']}", f"सबसे उपयुक्त: {t['n']['hi']} ({t['match']}%)। {t['d']['hi']}"
    else: en, hi = "Ask me about irrigation, schemes, loans or solar. Kisan Call Centre: 1800-180-1551.", "सिंचाई, योजना, ऋण या सौर के बारे में पूछें। किसान कॉल सेंटर: 1800-180-1551।"
    return jsonify(en=en, hi=hi)

INS_THRESH = {"Paddy": 120, "Wheat": 60, "Cotton": 90, "Maize": 80}  # seasonal rain mm below which crop is stressed (illustrative)
@app.post("/api/insurance/simulate")
@auth()
def insurance():
    """Parametric drought cover: payout scales with rainfall shortfall vs crop threshold. No field inspection."""
    u = g.user; rain = max(0, min(2000, float((request.get_json(silent=True) or {}).get("rain_mm", 100)))); th = INS_THRESH.get(u["crop"], 80)
    insured = int(u["land"]*25000); short = max(0, th-rain)/th; pay = int(insured*min(1, short*1.5)); paid = pay > 0
    return jsonify(crop=u["crop"], threshold=th, rain=rain, insured=insured, shortfall_pct=round(short*100), payout=pay, triggered=paid,
                   ref=("UPI"+secrets.token_hex(5).upper()) if paid else None, source="IMD gridded rainfall (simulated input) – illustrative")

def art(r, full=False):
    d = {"id": r["id"], "cat": r["cat"], "title": json.loads(r["title"]), "summ": json.loads(r["summ"]), "img": r["img"], "mins": r["mins"], "featured": r["featured"], "cta": r["cta"]}
    if full: d["body"] = json.loads(r["body"])
    return d
@app.get("/api/articles")
def articles():
    cat = request.args.get("cat"); qs = (request.args.get("q") or "").lower()
    rows = [art(r) for r in q("SELECT * FROM articles ORDER BY featured DESC, id")]
    return jsonify([a for a in rows if (not cat or a["cat"] == cat) and (not qs or qs in json.dumps(a, ensure_ascii=False).lower())])
@app.get("/api/articles/<int:i>")
def article(i):
    r = q("SELECT * FROM articles WHERE id=?", (i,), one=True); return (jsonify(art(r, True)) if r else (jsonify(error="not found"), 404))
@app.post("/api/toolkit/solar-pump")
@auth()
def toolkit():
    """Solar pump sizing + payback vs diesel. P(kW)=Q(m3/h)*H(m)/(367*eff)."""
    d = request.get_json(silent=True) or {}
    f = lambda k, df, lo, hi: max(lo, min(hi, float(d.get(k) or df)))
    flow, head, hrs, days, dp = f("flow",30,1,500), f("head",40,1,300), f("hours",6,1,14), f("days",200,10,365), f("diesel",92,50,150)
    eff = .5; kw = flow*head/(367*eff); hp = kw/.746; kwp = kw*1.3
    cost = kwp*55000; subsidy = cost*.6; net = cost-subsidy; litres = kw*hrs*days*.35; saving = litres*dp
    return jsonify(pump_kw=round(kw,1), pump_hp=round(hp,1), panel_kwp=round(kwp,1), cost=round(cost), subsidy=round(subsidy), farmer_pays=round(net), diesel_l_year=round(litres),
        saving_year=round(saving), payback_years=round(net/saving,1) if saving else None, co2_t_year=round(litres*2.68/1000,2),
        assumptions=["Pump efficiency 50%","Array = 1.3 x pump kW","Cost Rs 55,000/kWp (indicative)","Subsidy 60% (30% centre + 30% state) – varies by state","Diesel 0.35 L/kWh shaft energy"])
@app.get("/api/ml/info")
def ml_info(): return jsonify(models=[{"name": "Solar output forecaster", "type": "GradientBoostingRegressor", "r2": ml.METRICS["solar_r2"], "inputs": "hour, cloud cover, temperature"},
 {"name": "Credit default-risk", "type": "LogisticRegression (explainable)", "auc": ml.METRICS["credit_auc"], "inputs": "5 behavioural factors"},
 {"name": "Groundwater stress", "type": "Logistic rule model", "inputs": "pumping vs crop need"}, {"name": "Solar fault detector", "type": "Z-score anomaly", "inputs": "daily output"},
 {"name": "Crop Doctor", "type": "HSV segmentation + lesion blob analysis (+ optional Claude Vision)", "inputs": "leaf photo"}], note="Trained on simulated data; retrain on pilot data.")
@app.get("/")
def index(): return send_from_directory("static", "index.html")
init()
if __name__ == "__main__": app.run(debug=os.environ.get("KU_DEBUG") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
