"""Trained ML models (scikit-learn). Trained on physics/agronomy-simulated data at first run, cached in models/.
Honest note: replace training data with real meter + repayment data from pilots; the pipeline and API stay the same."""
import os, json, math, numpy as np, joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, roc_auc_score
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"); os.makedirs(D, exist_ok=True)
FEATS = ["punctuality", "solar_use", "water_eff", "tenure", "schemes"]
def _cf(h, cloud, temp):
    clear = np.where((h >= 6) & (h <= 18), np.exp(-((h-12)/3.2)**2/2), 0)
    return .85*clear*(1-.75*cloud)*(1-.004*np.maximum(0, temp-25))
def train():
    rng = np.random.default_rng(42); n = 8000
    h = rng.integers(0, 24, n); cl = rng.random(n); tp = rng.uniform(18, 46, n)
    y = np.clip(_cf(h, cl, tp)+rng.normal(0, .02, n), 0, 1); X = np.c_[h, cl, tp]
    Xa, Xb, ya, yb = train_test_split(X, y, test_size=.2, random_state=1)
    sol = GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=1).fit(Xa, ya)
    m = {"solar_r2": round(r2_score(yb, sol.predict(Xb)), 3)}
    F = rng.random((n, 5)); risk = -9*(F @ np.array([.4, .25, .2, .1, .05])-.55)+rng.normal(0, .2, n)-1.2
    lab = (rng.random(n) < 1/(1+np.exp(-risk))).astype(int)
    Fa, Fb, la, lb = train_test_split(F, lab, test_size=.2, random_state=1)
    cr = LogisticRegression().fit(Fa, la); m["credit_auc"] = round(roc_auc_score(lb, cr.predict_proba(Fb)[:, 1]), 3)
    m["credit_mean"] = F.mean(0).tolist(); joblib.dump((sol, cr), f"{D}/models.joblib"); json.dump(m, open(f"{D}/metrics.json", "w")); return sol, cr, m
try: SOLAR, CREDIT = joblib.load(f"{D}/models.joblib"); METRICS = json.load(open(f"{D}/metrics.json"))
except Exception: SOLAR, CREDIT, METRICS = train()
def solar_cf(cloud, temp):
    return np.clip(SOLAR.predict(np.array([[h, cloud, temp] for h in range(24)])), 0, 1)
def default_prob(f):
    x = np.array([[f[k] for k in FEATS]]); p = float(CREDIT.predict_proba(x)[0, 1])
    c = CREDIT.coef_[0]*(x[0]-np.array(METRICS["credit_mean"])); return p, {k: round(float(-v), 2) for k, v in zip(FEATS, c)}
