import streamlit as st
import pandas as pd
import requests
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.title("AI Startup Word Cloud")

# Airtable credentials
AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Data_Collection_Form"

url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}

response = requests.get(url, headers=headers)
data = response.json()["records"]

words = []

for record in data:
    fields = record.get("fields", {})
    
    # Access the column "AI word"
    if "AI word" in fields and fields["AI word"]:
        words.append(str(fields["AI word"]).lower())

# Count word frequency
word_counts = Counter(words)

# Convert to dataframe
df = pd.DataFrame(word_counts.items(), columns=["Word", "Frequency"])
df = df.sort_values("Frequency", ascending=False)

# Create text for wordcloud
text = " ".join(words)

# Generate word cloud
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