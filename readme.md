# 🧠 WikECD: Wikipedia Efficient Compression & Decompression

**WikECD** is a Python library and command-line toolkit for **efficiently compressing and retrieving Wikipedia revision histories**.  
It implements a **knapsack-optimized partitioning algorithm** to balance **storage space** and **retrieval time**, enabling fast access to any revision without fully decompressing the entire article.

---

## 🌍 Overview

Wikipedia articles have thousands of revisions — each slightly different from the previous one.  
Naïvely storing all versions wastes storage, while delta-compression makes retrieval slow.  
**WikECD** solves this trade-off by modeling revision storage as an **optimization problem**, finding an **optimal partition** of revisions that minimizes space under a fixed time cost constraint.

---

## ⚙️ Core Idea

Given a sequence of article revisions:

\[
R = \{r_0, r_1, ..., r_n\}
\]

Each revision has a size:

\[
S = \{s_i \mid s_i = ||r_i||, 0 \le i \le n\}
\]

We can store revisions as:
- **Full copies** (large space, fast retrieval), or
- **Deltas** (small space, slower retrieval).

### 🎯 Objective
Find an optimal partition \( P = \{p_1, p_2, ..., p_k\} \) such that:

- **Space cost** \( \sum f^-(p_j) \) is minimized  
- **Time cost** \( \sum t(p_j) \) ≤ fixed time budget \( C \)

This reduces to a **0/1 Knapsack problem**, where:
- Items = revision pairs  
- Profit = memory saved  
- Weight = retrieval cost  
- Capacity = maximum time cost

---

## 🧮 Algorithm Summary

| Step | Description |
|------|--------------|
| 1️⃣ | Compute revision sizes and approximate diffs: `||dr_i|| ≈ 2|s_i - s_{i-1}|` |
| 2️⃣ | Compute memory saved and time cost for each diff |
| 3️⃣ | Solve 0/1 Knapsack to select optimal delta positions |
| 4️⃣ | Build partition set \( P \) based on selected transitions |
| 5️⃣ | Store full revisions (anchors) and deltas (patches) |
| 6️⃣ | Retrieval reconstructs any revision by applying minimal diffs from nearest anchor |

---

## Features

| Category | Feature |
|-----------|----------|
| 🗂️ **Data Sources** | - Wikipedia API (with continuation & polite User-Agent)<br>- Wikipedia XML dump parser |
| 📦 **Compression** | - Knapsack-based optimal partitioning<br>- Linear diff approximation<br>- Metadata (IDs, timestamps, partitions) |
| 💾 **Storage** | - JSON+gzip compressed format<br>- Supports serialization/deserialization |
| 🔍 **Retrieval** | - Retrieve by index range<br>- Retrieve by revision ID<br>- Retrieve by timestamp range |
| ⚙️ **CLI Tool** | - `wikecd compress-api`<br>- `wikecd compress-xml`<br>- `wikecd retrieve`<br>- `wikecd retrieve-by-id`<br>- `wikecd retrieve-by-time` |
| 🧠 **Extensibility** | - Pluggable diffing algorithms<br>- SQLite backend (planned)<br>- FastAPI microservice (planned) |

---

## 🧱 Architecture

WikECD/\
├── sources/\
│   ├── base.py\
│   ├── xml_parser.py\
│   └── api_client.py\
│       # Data extraction (API, XML)\
├── compression/\
│   ├── diff_utils.py\
│   ├── knapsack.py\
│   ├── partitioner.py\
│   └── compressor.py\
│       # Knapsack-based compression\
├── retrieval/\
│   ├── retrieval.py\
│   └── query.py\
│       # Efficient revision reconstruction\
├── storage/\
│   ├── compressed_store.py\
│   └── serializer.py\
│       # Compressed representation & persistence\
├── cli.py               # Command-line interface\
├── examples/            # Usage demos\
└── tests/               # Unit tests\

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/<yourusername>/WikECD.git
cd WikECD

# Install in editable/development mode
pip install -e .

Requires Python ≥ 3.9
Dependencies: requests, gzip, difflib
```
## Usage Examples
### 1. Compress using Wikipedia API
```
wikecd compress-api \
  --title "Python (programming language)" \
  --limit 40 \
  --out python.comp.gz \
  --user-agent "WikECD/0.1 (+https://github.com/you; contact: you@example.com)"
```
### 2. Retrieve by revision indices
```
wikecd retrieve \
  --in python.comp.gz \
  --start 10 \
  --length 5 \
  --print
```
Retrieves revisions [10..15] and prints the last one.

### 3. Retrieve by Revision ID
```
wikecd retrieve-by-id \
  --in python.comp.gz \
  --ids 123456789,123456790 \
  --print
```

Retrieves the specified revision IDs.

### 4. Retrieve by Timestamp Range
```
wikecd retrieve-by-time \
  --in python.comp.gz \
  --start-ts 2024-01-01 \
  --end-ts 2024-02-01 \
  --print
```

Retrieves all revisions made between Jan 1 and Feb 1, 2024.

## Programmatic API

Compress and save:
```
from WikECD.sources.api_client import MediaWikiAPISource
from WikECD.compression.compressor import compress_article
from WikECD.storage.serializer import save

src = MediaWikiAPISource(user_agent="WikECD/0.1 (+https://github.com/you; contact: you@example.com)")
revs = list(src.get_revisions(title="Python (programming language)", limit=40))
article = compress_article("Python (programming language)", revs)
base_texts = {b: revs[b].text for b in article.anchors}
save("python.comp.gz", article, base_texts)
```

Load and retrieve:
```
from WikECD.storage.serializer import load
from WikECD.retrieval.query import retrieve_by_time

article, base_texts = load("python.comp.gz")
texts = retrieve_by_time(article, base_texts, start="2024-01-01", end="2024-01-31")
```
## Metadata Stored

Each compressed article includes:
```
{
  "title": "Python (programming language)",
  "anchors": [0, 7, 13, 21],
  "meta": {
    "count": 40,
    "revids": [...],
    "timestamps": [...],
    "partitions": [[0,1,2,3],[4,5,6],...]
  }
}
```
