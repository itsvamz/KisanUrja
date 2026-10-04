# KisanUrja Grid – MVP
Flask + SQLite + vanilla JS. Bilingual (EN/हिं), left-sidebar app, token login, role-based (farmer / DISCOM officer).

## Run
    pip install -r requirements.txt
    python app.py     # http://localhost:5000
Demo: farmer 9999900001 / officer 9999900002, password demo123. Delete kisanurja.db to reset.

## Modules (all in app.py)
- Solar Cluster: weighted max-min fair-share allocation engine (water-filling), Jain fairness, mock UPI ledger
- Water: groundwater stress (logistic), solar anomaly detection (z-score), irrigation advisor (weather+solar)
- Crop Doctor: camera/upload -> HSV colour segmentation (Pillow+NumPy). Set ANTHROPIC_API_KEY for an AI second opinion
- Schemes: rule-based matcher + official links; Credit: explainable weighted score; Carbon: MRV-style estimator
## Honest limits
Readings/weather are seeded synthetic data; swap `weather()` for IMD/Open-Meteo and `readings` for MQTT meters.
Crop model is a heuristic, not a trained disease classifier. Images load from loremflickr (needs internet).

## Production
    docker build -t kisanurja . && docker run -p 8000:8000 -v ku-data:/data kisanurja
    pytest tests          # 10 tests
Env: KU_DB (db path), PORT, KU_DEBUG=1 (dev only), ANTHROPIC_API_KEY (optional).
Done: hashed passwords + hashed, expiring tokens (7d), login rate-limit, input validation, XSS escaping, security headers/CSP, 8 MB upload cap, health check, gunicorn, Docker, tests.
Before real users: rotate demo passwords/remove demo seed, use Postgres, put behind HTTPS (nginx/ALB), use Redis for rate-limits, add OTP login, DPDP consent screens + privacy policy, real data feeds (MQTT meters, IMD), self-host images/fonts and drop 'unsafe-inline' CSP.

## v3 additions
- OTP login (KU_DEV_OTP=0 in prod + wire SMS gateway in `otp_req`), password login, register
- ml.py: trained GradientBoosting solar forecaster + logistic credit-risk model (cached in models/, metrics at /api/ml/info). Trained on simulated data – retrain on pilot data.
- Crop Doctor: HSV segmentation + lesion-blob counting; optional Claude Vision second opinion
- Learn: bilingual blog/guides (content.py), search, categories, featured; Solar Toolkit: pump sizing, subsidy and diesel payback calculator
