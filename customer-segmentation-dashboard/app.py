import joblib
import plotly.express as px
import streamlit as st

from src.data import load_customers

MODEL_PATH = "artifacts/model.joblib"
SCALER_PATH = "artifacts/scaler.joblib"

st.set_page_config(page_title="Customer Segmentation", page_icon="👥")

st.title("👥 Customer Segmentation Dashboard")

if "model" not in st.session_state:
    st.session_state.model = joblib.load(MODEL_PATH)
    st.session_state.scaler = joblib.load(SCALER_PATH)


def assign_cluster(row):
    X = st.session_state.scaler.transform([row])
    return int(st.session_state.model.predict(X)[0])


customers = load_customers()
customers["cluster"] = st.session_state.model.predict(
    st.session_state.scaler.transform(customers)
)

fig = px.scatter(
    customers,
    x="income",
    y="spend_score",
    color=customers["cluster"].astype(str),
    hover_data=["age", "visits_per_month"],
    title="Customer Segments",
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Assign a new customer")

age = st.number_input("Age", 18, 80, 30)
income = st.number_input("Income", 10000, 200000, 60000)
spend_score = st.slider("Spend Score", 1, 100, 50)
visits = st.slider("Visits per Month", 1, 30, 6)

if st.button("Assign Cluster"):
    cluster = assign_cluster([age, income, spend_score, visits])
    st.success(f"Assigned Cluster: {cluster}")