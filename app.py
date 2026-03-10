import streamlit as st
import pandas as pd
import requests
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.title("AI Startup Word Cloud")

# Airtable credentials from Streamlit secrets
API_KEY = st.secrets["AIRTABLE_API_KEY"]
BASE_ID = st.secrets["BASE_ID"]

TABLE_NAME = "Data_Collection_Form"

url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, headers=headers)
data_json = response.json()

# Handle API errors safely
if "records" not in data_json:
    st.error("Error retrieving Airtable data")
    st.write(data_json)
    st.stop()

data = data_json["records"]

words = []

for record in data:
    fields = record.get("fields", {})

    if "AI word" in fields and fields["AI word"]:
        words.append(str(fields["AI word"]).lower())

# Count frequency
word_counts = Counter(words)

df = pd.DataFrame(word_counts.items(), columns=["Word", "Frequency"])
df = df.sort_values("Frequency", ascending=False)

text = " ".join(words)

wordcloud = WordCloud(
    width=1600,
    height=800,
    background_color="white",
    colormap="Greys",
    max_words=300,
    prefer_horizontal=0.9
).generate(text)

fig, ax = plt.subplots(figsize=(16,8))
ax.imshow(wordcloud, interpolation="bilinear")
ax.axis("off")

st.pyplot(fig)