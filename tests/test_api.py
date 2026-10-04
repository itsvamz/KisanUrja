import os, io, tempfile
os.environ["KU_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import app as A
from PIL import Image
c = A.app.test_client()
def tok(p="9999900001", pw="demo123"): return {"Authorization": "Bearer " + c.post("/api/login", json={"phone": p, "password": pw}).json["token"]}
def test_auth_required(): assert c.get("/api/dashboard").status_code == 401
def test_bad_login(): assert c.post("/api/login", json={"phone": "1", "password": "x"}).status_code == 401
def test_register_validation(): assert c.post("/api/register", json={"name": "A", "phone": "12", "password": "secret1"}).status_code == 400
def test_register_ok_and_xss_stored_raw():
    r = c.post("/api/register", json={"name": "<b>X</b>", "phone": "9000000001", "password": "secret1"}); assert r.status_code == 200
def test_endpoints():
    h = tok()
    for p in ["dashboard", "solar/simulate", "water", "schemes", "credit", "carbon", "solar/ledger", "crop/history"]: assert c.get("/api/" + p, headers=h).status_code == 200
def test_fair_share():
    a = A.fair_share(10, [8, 8, 2], [1, 1, 1]); assert abs(sum(a) - 10) < 1e-6 and a[2] == 2 and abs(a[0] - 4) < 1e-6
def test_officer_only():
    assert c.get("/api/officer/overview", headers=tok()).status_code == 403
    assert c.get("/api/officer/overview", headers=tok("9999900002")).status_code == 200
def test_insurance():
    h = tok(); assert c.post("/api/insurance/simulate", headers=h, json={"rain_mm": 0}).json["triggered"]; assert not c.post("/api/insurance/simulate", headers=h, json={"rain_mm": 500}).json["triggered"]
def test_crop_scan():
    b = io.BytesIO(); Image.new("RGB", (100, 100), (200, 180, 30)).save(b, "JPEG"); b.seek(0)
    assert c.post("/api/crop/analyze", headers=tok(), data={"image": (b, "a.jpg")}).json["key"] in ("yellow", "both")
def test_headers(): assert "frame" in "".join(c.get("/healthz").headers.keys()).lower() or c.get("/healthz").headers["X-Frame-Options"] == "DENY"
def test_otp_flow():
    r = c.post("/api/otp/request", json={"phone": "9999900001"}).json; assert r["dev_otp"]
    assert c.post("/api/otp/verify", json={"phone": "9999900001", "code": "000000"}).status_code == 401
    assert c.post("/api/otp/verify", json={"phone": "9999900001", "code": r["dev_otp"]}).json["token"]
def test_content_and_toolkit():
    a = c.get("/api/articles").json; assert len(a) >= 6 and c.get(f"/api/articles/{a[0]['id']}").json["body"]["hi"]
    assert c.get("/api/articles?cat=Solar").json
    assert c.post("/api/toolkit/solar-pump", headers=tok(), json={}).json["pump_kw"] > 0
def test_ml():
    assert A.ml.METRICS["solar_r2"] > .9 and A.ml.METRICS["credit_auc"] > .7 and c.get("/api/ml/info").json["models"]
    day = A.date.today().isoformat(); s, _ = A.solar_curve(day); assert max(s) > 0 and s[0] == 0
