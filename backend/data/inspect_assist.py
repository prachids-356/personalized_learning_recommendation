import urllib.request
import pandas as pd
import io

url = "https://huggingface.co/datasets/Unggi/assistment09_raw_data/resolve/main/skill_builder_data.csv"
print(f"Downloading from {url}...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        # Read first 1MB of the file and load it using latin1 or ISO-8859-1
        chunk = response.read(1024 * 1024)
        df = pd.read_csv(io.BytesIO(chunk), nrows=10, encoding="ISO-8859-1")
        print("Successfully loaded CSV preview! Columns:")
        print(df.columns.tolist())
        print("\nFirst row preview:")
        print(df.iloc[0].to_dict())
except Exception as e:
    print(f"Error: {e}")
