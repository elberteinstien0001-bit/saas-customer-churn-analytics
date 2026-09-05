# Project Guide — SaaS Customer Churn Analytics
### A beginner-friendly walkthrough of every file, command, and what it's doing

---

## 0. The big picture (read this first)

Think of this project as a pipeline — data flows through four stages, each one a
folder in your repo:

```
[1] Generate raw data      →  churn_analytics.db (SQLite database)
        ↓  (01_generate_data.py)
[2] Clean + engineer features with SQL  →  cleaned_customer_data.csv
        ↓  (02_sql_feature_engineering.py)
[3] Model with Python (ML)  →  final_customer_analytics.csv
        ↓  (03_ml_segmentation_churn.py)
[4] Visualize in Power BI   →  SaaS_Customer_Health.pbix (the dashboard)
```

Each script/file below belongs to one of those four stages. Once you understand
the stage a file belongs to, the file itself becomes much easier to read.

---

## 1. Root-level Python scripts (Stage 1–3: the engine room)

### `01_generate_data.py` — creates the database

**What it does:** Since this is a *portfolio* project (not a real company), there's
no real customer data to pull from. This script **invents** realistic-looking data
and saves it into a SQLite database file (`churn_analytics.db`).

**Key concepts explained:**

| Code | What it means |
|---|---|
| `import sqlite3` | SQLite is a tiny, file-based database — no server needed, the whole database lives in one `.db` file. Python has built-in support for it. |
| `conn = sqlite3.connect('churn_analytics.db')` | Opens (or creates, if it doesn't exist) that database file. `conn` is your "connection" to it — almost everything else routes through this object. |
| `cursor = conn.cursor()` | A cursor is like a pointer/remote control you use to run SQL commands through the connection. |
| `np.random.seed(42)` | **This is important.** It forces the "random" numbers to always come out the same way every time you run the script. That's why re-running the pipeline always gives you the same 1,000 customers, the same 29.30% churn rate, etc. Without this line, every run would generate different (random) data. |
| `cursor.executescript('''...''')` | Runs multiple SQL statements at once — here it's three `CREATE TABLE` statements that define the shape of your data (columns, types). |
| `for cid in range(101, 101 + num_customers):` | A loop that builds 1,000 fake customers, one per iteration, with a customer ID starting at 101. |
| `np.random.choice(regions, p=[0.4, 0.3, 0.2, 0.1])` | Randomly picks a region, but weighted — 40% chance of North America, 30% Europe, etc. This is what makes the fake data look realistic instead of perfectly even. |
| `cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers_data)` | Inserts all 1,000 customer rows in one go. The `?` marks are placeholders — Python safely substitutes in your data (this avoids SQL injection bugs). |
| The subscription/transaction loop | For each customer, it randomly decides if they churned (30% chance) or stayed active, generates a subscription record, and then generates a recurring transaction every ~30 days for as long as that subscription was active. |
| `conn.commit()` | Actually saves all your changes to the `.db` file. Nothing is permanently written until you commit. |
| `conn.close()` | Closes the connection cleanly. |

**Command to run it:**
```bash
python 01_generate_data.py
```
**Output:** a file called `churn_analytics.db` appears in your folder, containing 3 tables: `customers`, `subscriptions`, `transactions`.

---

### `02_sql_feature_engineering.py` — turns raw data into analysis-ready features

**What it does:** Raw transaction-level data isn't useful for a dashboard. This
script asks SQL to **summarize** the data down to one row per customer, with
metrics a business actually cares about (how recently did they buy, how often,
how much did they spend, are they still a customer).

**Key concepts explained:**

| Code | What it means |
|---|---|
| `WITH CustomerTransactions AS (...)` | This is a **CTE** (Common Table Expression) — basically a temporary, named mini-table you can build once and reuse. Think of it as a labeled sub-query. |
| `COUNT(transaction_id) AS frequency` | Counts how many transactions each customer made — this is the "Frequency" in RFM. |
| `SUM(amount) AS monetary_value` | Total money spent — the "Monetary" in RFM. |
| `MAX(transaction_date)` / `MIN(transaction_date)` | Their most recent and very first purchase dates. |
| `GROUP BY customer_id` | Collapses many transaction rows into one summary row **per customer**. Without this, `COUNT`/`SUM` would just total everything into one giant number. |
| `LEFT JOIN CustomerTransactions t ON c.customer_id = t.customer_id` | Combines the customer table with the transaction summary. `LEFT JOIN` means: keep every customer even if they have zero transactions (a `JOIN` alone would drop them). |
| `COALESCE(t.frequency, 0)` | If a customer has no transactions, `t.frequency` would be empty (`NULL`). `COALESCE` says "if it's empty, use 0 instead." |
| `JULIANDAY('2026-08-01') - JULIANDAY(t.last_transaction_date)` | SQLite's way of subtracting two dates to get a number of days. `JULIANDAY()` converts a date into a single number (days since a fixed reference point), so subtracting two of them gives you the day gap — this is how "Recency" (days since last purchase) is calculated. |
| `CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END AS is_churned` | Converts a text label ("Cancelled"/"Active") into a clean 0/1 flag that a machine learning model can actually use. |
| `AVG(total_revenue) OVER (PARTITION BY region)` | This is a **window function**. Unlike `GROUP BY` (which collapses rows), a window function calculates something (here, the average revenue) *per region*, but keeps every individual customer row intact — so each customer can see "how does my spending compare to my region's average?" |
| `ROW_NUMBER() OVER (PARTITION BY region ORDER BY total_revenue DESC)` | Ranks each customer within their own region, #1 being the top spender in that region. |
| `pd.read_sql_query(rfm_query, conn)` | Runs that whole SQL query and loads the result straight into a pandas DataFrame (a spreadsheet-like table in Python). |
| `rfm_df.to_csv('customer_rfm_churn_data.csv', index=False)` | Saves that table as a CSV file. `index=False` means don't add pandas' internal row-number column to the file. |

**Command to run it:**
```bash
python 02_sql_feature_engineering.py
```
**Output:** `customer_rfm_churn_data.csv` — one row per customer, with recency, frequency, revenue, tenure, and churn flag.

---

### `03_ml_segmentation_churn.py` — the machine learning stage

**What it does:** Two separate ML tasks happen here:
1. **Segmentation** (unsupervised) — group similar customers together without being told the "right" answer.
2. **Churn prediction** (supervised) — train a model on customers whose outcome (churned or not) we already know, so it can predict the risk for anyone.

**Key concepts explained:**

| Code | What it means |
|---|---|
| `pd.qcut(df['recency_days'], 5, labels=[5, 4, 3, 2, 1])` | Splits customers into 5 equal-sized buckets (quintiles) based on recency, and scores them 1–5. Notice the labels are reversed (`[5,4,3,2,1]`) — that's intentional: *lower* recency (they bought recently) should get a *higher* score, since recent buyers are more valuable. |
| `df['R_Score'] + df['F_Score'] + df['M_Score']` | Adds the three RFM scores into one combined `RFM_Score` (ranges roughly 3–15) — a simple, explainable way to rank overall customer value. |
| `StandardScaler().fit_transform(df[rfm_features])` | Machine learning clustering is sensitive to scale — "total_revenue" might range in thousands while "frequency" ranges in tens. `StandardScaler` rescales every feature to the same range (mean 0, standard deviation 1) so no single feature unfairly dominates the clustering. |
| `KMeans(n_clusters=4, random_state=42, n_init=10)` | **K-Means** is an algorithm that automatically groups data points into a chosen number of clusters (here, 4) based on similarity. `random_state=42` makes it reproducible (same reasoning as `np.random.seed` earlier). `n_init=10` means it tries 10 different random starting points and keeps the best result. |
| `df['Cluster_ID'] = kmeans.fit_predict(X_scaled)` | Runs the clustering and assigns each customer a cluster number (0, 1, 2, or 3) — but these numbers alone mean nothing to a business user. |
| `cluster_means = df.groupby('Cluster_ID')['total_revenue'].mean().sort_values()` | Figures out which cluster actually has the highest/lowest average spending, so we can... |
| `cluster_mapping = {...}` | ...translate raw cluster numbers into human-readable labels like "VIP / High Spender" or "Low-Value / At-Risk". |
| `train_test_split(X, y, test_size=0.25, ..., stratify=y)` | Splits your data into a training set (75%) the model learns from, and a test set (25%) used to check how well it actually predicts on data it's never seen. `stratify=y` ensures both sets have the same churn/non-churn ratio, so the test is fair. |
| `RandomForestClassifier(n_estimators=100, random_state=42)` | A **Random Forest** builds 100 different decision trees (`n_estimators=100`), each trained slightly differently, then averages their votes. This tends to be more accurate and less prone to overfitting than a single decision tree. |
| `rf_model.fit(X_train, y_train)` | This is the actual "learning" step — the model studies the training data and figures out patterns that predict churn. |
| `rf_model.predict_proba(X[features])[:, 1]` | Instead of a hard yes/no, this gives a *probability* of churn (0.0 to 1.0) for every customer — much more useful for ranking risk. |
| `pd.cut(df['Churn_Probability'], bins=[-0.01, 0.3, 0.7, 1.0], labels=[...])` | Converts that continuous probability into 3 simple buckets: Low / Medium / High Risk — this is what feeds the "Risk_Category" filter in your Power BI dashboard. |
| `classification_report(y_test, rf_model.predict(X_test))` | Prints precision, recall, and F1-score — standard metrics for judging how good a classification model is. This only runs on the held-out test set, so it's an honest measure of performance. |

**Command to run it:**
```bash
python 03_ml_segmentation_churn.py
```
**Output:** `final_customer_analytics.csv` — the fully enriched dataset (RFM scores + segment + churn probability + risk category). **This is the file your Power BI dashboard actually reads from.**

---

## 2. `sql/` folder — the same logic, organized for a portfolio

| File | Purpose |
|---|---|
| `01_schema_setup.sql` | Just the `CREATE TABLE` statements — shows a reviewer your database design skills without needing to read the whole Python script. |
| `02_data_cleaning.sql` | Standalone cleaning logic (removing duplicate transactions, fixing orphaned foreign keys, standardizing text). This demonstrates real-world data-cleaning SQL patterns. |
| `03_churn_analysis_queries.sql` | The main RFM feature-engineering query, plus 3 bonus reporting queries (churn rate by plan, LTV by plan, revenue by region) that double-check your Power BI numbers using pure SQL. |

**How to run any of these yourself** (to prove they work against your actual database):
```bash
sqlite3 churn_analytics.db < sql/01_schema_setup.sql
sqlite3 churn_analytics.db < sql/02_data_cleaning.sql
sqlite3 churn_analytics.db < sql/03_churn_analysis_queries.sql
```
Or, if you have the VS Code **SQLite** extension installed, right-click `churn_analytics.db` → "Open Database", then open any `.sql` file and click "Run Query".

---

## 3. `python/` folder — notebooks (interactive versions of the scripts)

| File | Purpose |
|---|---|
| `eda_and_preprocessing.ipynb` | Covers Stage 1 + cleaning + exploration. **EDA** stands for **Exploratory Data Analysis** — looking at histograms, correlations, and churn-rate breakdowns *before* modeling, to sanity-check the data and spot patterns. |
| `churn_prediction_model.ipynb` | Covers Stage 3 (RFM scoring, K-Means, Random Forest) — same code as `03_ml_segmentation_churn.py`, but broken into cells with explanations and charts, which is the standard way ML work is presented for a portfolio (notebooks let you show your thinking step-by-step, not just a final script). |

**Why notebooks vs. `.py` scripts?** Scripts (`.py`) are meant to be *run end-to-end, unattended* (e.g. as part of an automated pipeline). Notebooks (`.ipynb`) are meant to be *read and run cell-by-cell*, so a reviewer can see your reasoning, look at your charts, and re-run individual steps. Portfolios usually want notebooks because they double as documentation.

**How to open/run them:**
1. Install Jupyter support: `pip install jupyter` (or in VS Code, install the **Jupyter** extension — it can run `.ipynb` files natively).
2. In VS Code, just click the file — it opens as a notebook with "Run" buttons on each cell.
3. Run cells top to bottom, in order (each one depends on variables created in the cells above it).

---

## 4. `power_bi/` folder

| File | Purpose |
|---|---|
| `SaaS_Customer_Health.pbix` | The actual Power BI report file — opens in **Power BI Desktop** (free download from Microsoft). Contains all your dashboard pages, visuals, and filters. |
| `dax_measures.md` | Documentation of the calculated fields (called **measures**) used in the report — e.g. `Total Revenue`, `Churn Rate`. **DAX** (Data Analysis Expressions) is the formula language Power BI uses, similar in spirit to Excel formulas but built for whole tables/relationships. |

**Important honesty note:** the DAX formulas in that file are *reconstructed* to match what the dashboard displays — not copy-pasted from the real file, because Power BI compiles measures into its binary data model, which can't be read as plain text. To get the 100%-accurate originals: open the `.pbix` in Power BI Desktop → **Model view** (left sidebar) → click each measure → the real formula shows in the formula bar.

---

## 5. `data/` folder

| File | What's in it | Where it came from |
|---|---|---|
| `churn_analytics.db` | The raw SQLite database — 3 tables (customers, subscriptions, transactions) | Output of `01_generate_data.py` |
| `raw_customer_data.csv` | A flat, denormalized version of the database (one row per transaction, joined with customer + subscription info) — messy on purpose, with nulls where subscriptions are still active | A SQL join run directly against `churn_analytics.db` |
| `cleaned_customer_data.csv` | One row per customer, RFM features calculated | Output of `02_sql_feature_engineering.py` (same content as `customer_rfm_churn_data.csv`) |
| `final_customer_analytics.csv` | The final enriched dataset — RFM + segment + churn probability + risk tier | Output of `03_ml_segmentation_churn.py`. **This is what Power BI reads.** |

---

## 6. `docs/` folder

| File | Purpose |
|---|---|
| `dashboard_preview.png` | A screenshot of the live dashboard — used in your README so anyone browsing GitHub sees the result without opening Power BI. |
| `executive_summary.pdf` | A 1-page, non-technical summary (KPIs, key findings, recommended actions) — the kind of document you'd actually hand to a manager who doesn't want to read code. |

---

## 7. Command cheat-sheet (everything in one place)

### Environment setup
```bash
python -m venv venv                 # create an isolated Python environment
venv\Scripts\activate                # activate it (Windows)
source venv/bin/activate             # activate it (macOS/Linux)
pip install pandas numpy scikit-learn jupyter   # install required libraries
```

### Running the pipeline (in order — each step needs the previous one's output)
```bash
python 01_generate_data.py              # → churn_analytics.db
python 02_sql_feature_engineering.py    # → cleaned_customer_data.csv
python 03_ml_segmentation_churn.py      # → final_customer_analytics.csv
```

### Inspecting the database directly
```bash
sqlite3 churn_analytics.db
.tables                    # list all tables
.schema customers           # show a table's structure
SELECT COUNT(*) FROM customers;   # run any SQL query
.quit                      # exit
```

### Git — pushing your work to GitHub
```bash
git clone https://github.com/<your-username>/saas-customer-churn-analytics.git
git add .
git commit -m "Add SQL scripts, notebooks, and dashboard files"
git push origin main
```

### Comparing two files to check they truly match (verification)
```bash
code --diff file_a.py file_b.sql     # opens VS Code's side-by-side diff view
md5sum file_a.csv file_b.csv         # macOS/Linux — compares file fingerprints
Get-FileHash file_a.csv, file_b.csv -Algorithm MD5   # Windows PowerShell equivalent
```

---

## 8. Glossary (plain-English definitions)

- **SQLite** — a lightweight database stored as a single file, no server required.
- **CTE (`WITH ... AS`)** — a named, temporary sub-query you can reference like a table.
- **Window function (`OVER (PARTITION BY ...)`)** — calculates a value (like an average or rank) across a group of rows, without collapsing them into one row.
- **RFM** — Recency, Frequency, Monetary value — a classic, simple way to score customer value.
- **K-Means clustering** — an unsupervised ML algorithm that groups similar data points together into a chosen number of clusters.
- **Random Forest** — a supervised ML model made of many decision trees voting together, used here to predict churn probability.
- **Train/test split** — dividing data so the model learns from one part and is honestly evaluated on a part it's never seen.
- **DAX** — the formula language Power BI uses for calculated fields ("measures").
- **ODBC** — a standard driver interface that lets tools like Power BI connect to databases (like SQLite) that don't have a native connector.
