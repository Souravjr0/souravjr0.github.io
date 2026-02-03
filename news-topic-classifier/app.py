import streamlit as st

from src.predict import predict_topic

st.set_page_config(page_title="News Topic Classifier", page_icon="📰")

st.title("📰 News Topic Classifier")
st.write("Classify a news snippet into one of the trained topics.")

text = st.text_area("Paste a news paragraph", height=200)

if st.button("Predict"):
    if not text.strip():
        st.warning("Please enter some text.")
    else:
        result = predict_topic(text)
        st.success(f"Predicted Topic: {result['label']}")