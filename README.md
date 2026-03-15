## Mongo Finance App

MongoDB-backed version of the finance entry app.

### Setup

Set these environment variables before running:

- `MONGODB_URI`
- `MONGODB_DB`

Example:

```powershell
$env:MONGODB_URI="mongodb://localhost:27017"
$env:MONGODB_DB="finance_app"
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Seed sample data:

```powershell
python seed_mongo.py
```

Run:

```powershell
streamlit run app.py
```
