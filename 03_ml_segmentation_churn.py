import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

df = pd.read_csv('data/customer_rfm_churn_data.csv')
df['recency_days'] = df['recency_days'].fillna(df['recency_days'].max())

df['r_score'] = pd.qcut(df['recency_days'], 5, labels=[5, 4, 3, 2, 1]).astype(int)
df['f_score'] = pd.qcut(df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
df['m_score'] = pd.qcut(df['total_revenue'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
df['rfm_score'] = df['r_score'] + df['f_score'] + df['m_score']

rfm_features = ['recency_days', 'frequency', 'total_revenue']
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[rfm_features])

kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
df['cluster_id'] = kmeans.fit_predict(X_scaled)

cluster_means = df.groupby('cluster_id')['total_revenue'].mean().sort_values()
cluster_mapping = {
    cluster_means.index[0]: 'Low Value',
    cluster_means.index[1]: 'Mid Value',
    cluster_means.index[2]: 'High Value',
    cluster_means.index[3]: 'VIP'
}
df['customer_segment'] = df['cluster_id'].map(cluster_mapping)

features = ['recency_days', 'frequency', 'total_revenue', 'tenure_days', 'monthly_price', 'rfm_score']
X = df[features]
y = df['is_churned']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

df['churn_probability'] = rf.predict_proba(X[features])[:, 1]
df['risk_category'] = pd.cut(
    df['churn_probability'], 
    bins=[-0.01, 0.3, 0.7, 1.0], 
    labels=['Low', 'Medium', 'High']
)

print(classification_report(y_test, rf.predict(X_test)))

df.to_csv('data/final_customer_analytics.csv', index=False)