import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import requests
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.title("AI Startup Word Cloud")

st_autorefresh(interval=5000, key="refresh")

# Secrets from Streamlit
API_KEY = st.secrets["AIRTABLE_API_KEY"]
BASE_ID = st.secrets["BASE_ID"]

TABLE_NAME = "AI%20Startup%20Competition%20Progress%20Form%202025"

url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, headers=headers)
data_json = response.json()

# Error handling
if "records" not in data_json:
    st.error("Error retrieving Airtable data")
    st.write(data_json)
    st.stop()

records = data_json["records"]

words = []

for record in records:
    fields = record.get("fields", {})
    if "AI word" in fields:
        words.append(fields["AI word"].lower())

if len(words) == 0:
    st.warning("No words submitted yet.")
    st.stop()

# Count frequencies
word_counts = Counter(words)

# Leaderboard
df = pd.DataFrame(word_counts.items(), columns=["Word", "Frequency"])
df = df.sort_values("Frequency", ascending=False)

st.subheader("Top Words")
st.dataframe(df)

# Word cloud
text = " ".join(words)

wordcloud = WordCloud(
    width=1600,
    height=800,
    background_color="white",
    colormap="Greys",
    max_words=200
).generate(text)

fig, ax = plt.subplots(figsize=(14,7))
ax.imshow(wordcloud, interpolation="bilinear")
ax.axis("off")

st.pyplot(fig)