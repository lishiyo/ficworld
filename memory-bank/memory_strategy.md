# Memory Strategy

The memory layer’s job is to give every agent fast, emotionally-relevant recall of thousands of past events without blowing the LLM’s context window.

We'll be using a high context window so we won't even need vector search for short story v1. However at larger book sizes we may want to switch to ChromaLocal (`pip install chromadb`):

```python
from story_agents.vector_drivers import ChromaLocal
memory = ChromaLocal(path=".chroma", embedding_fn=embed)
```

### Emotional-RAG & mood-conditioned recall

Emotional RAG retrieves memories that match both semantic similarity and the agent’s current mood vector. Any vector DB that lets you store extra numeric fields works:
```
{
  "id": "ev123",
  "vector": [...],              // embedding
  "metadata": {
     "speaker": "Sir Rowan",
     "ts": 4312,                // seconds since story start
     "mood": [0.2,0.1,0,0.1,0,0.6]  // joy, fear, ...
  }
}
```

Chroma and Weaviate support JSON metadata filters natively, so you can pre-filter on speaker="Sir Rowan” and then score by mood_dot() inside Python.

Below is a compact architectural guide for running our memory layer on Chroma—no extra vector-DB required. The key idea is to store every memory chunk in a single or per-project collection with rich metadata (project_id, character_id, scene, mood, type), then retrieve with Chroma’s $and / $or filters plus similarity search. Chroma already supports OpenAI/DeepSeek embeddings, logical metadata filters, persistent or in-memory servers, and scales from laptop demos to Docker micro-services.

Why Chroma fits multi-tenant storytelling

| Need                              | Chroma feature                                                                                                               | Notes                                          |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Fast semantic recall**          | HNSW/IVF indexes in local or remote mode ([anderfernandez.com][1], [Chroma Docs][2])                                         | <10 ms for 50 k vectors on-box.                |
| **Project & character isolation** | Metadata filters (`where={"project_id":"p123","character_id":"Alice"}`) ([Chroma Docs][3], [Chroma Docs][4])                 | Works inside one collection or across many.    |
| **Logical conditions**            | `$and`, `$or`, `$gt`, `$in` operators for complex queries ([Chroma Docs][3], [Stack Overflow][5])                            | E.g. “this project AND (Alice OR Bob)”.        |
| **Embeddings plug-ins**           | Pass any embedding function; OpenAI shown in docs + cookbook ([OpenAI Cookbook][6], [Chroma Docs][7])                        | Swap to DeepSeek by changing the embed fn.     |
| **No extra infra (dev)**          | `Chroma(persist_directory=…)` or `EphemeralClient()` for tests ([Chroma Docs][2])                                            | Prod: run `chromadb` docker for shared access. |
| **Scalable persistence**          | Collections live in SQLite/Parquet; you can shard by project path or collection name ([Chroma Docs][8], [Stack Overflow][9]) | One-path-per-user avoids write locking.        |

## Memory schema and Filters

```json
{
  "id": "evt_98765",
  "embedding": [ … 1536 floats … ],
  "metadata": {
    "project_id": "chronicles-001",
    "character_id": "SirRowan",
    "scene": 4,
    "ts": 4312,            // seconds since story start
    "mood": [0.1,0.6,0,0,0,0.3],  // joy, fear… (optional)
    "type": "dialogue"     // or "action" / "world"
  },
  "document": "Sir Rowan grips his bleeding arm and refuses to yield."
}
```

Retrieval query for Rowan’s fear-aligned memories inside scene ≤ 4:
```json
where = {
    "$and": [
      {"project_id": "chronicles-001"},
      {"character_id": "SirRowan"},
      {"scene": {"$lte": 4}}
    ]
}
results = collection.query(
    query_embeddings=[query_vec],
    n_results=8,
    where=where
)
```

Chroma combines the metadata filter first, then does cosine/inner-product ranking on the remaining vectors.

For MVP we only have 1 user, but eventually we would want to allow multiple users to be creating stories with this project, so we will need multi-tenancy. We'll want to be able to filter by project_id and character_id at minimum.

### Hooking Emotional-RAG

Store mood: embed a 6-D mood vector or a "dominant_mood":"fear" tag inside metadata.

Query boost: after Chroma returns top-k semantic results, re-rank in Python:

```python
for mem in results:
    sim = dot(q_vec, mem.embedding)
    emo = dot(q_mood, mem.metadata["mood"])
    mem.score = sim * (1 + emo)
```

This reproduces Emotional-RAG’s mood-congruent weighting without changing Chroma internals (vectors stay 1536-D).


### Inner-monologue & planning traces

Memories you’d actually write to Chroma:

| Content                  | Store?               | Why                                                                                                     |
| ------------------------ | -------------------- | ------------------------------------------------------------------------------------------------------- |
| **Narrator prose**       | **Yes (summarised)** | Used for “what happened” recall in later chapters.                                                      |
| **Dialogue/action line** | Yes                  | Agents quote or reflect on it later.                                                                    |
| **Inner monologue**      | *Sometimes*          | Mark with `"type":"thought"`; store only if it reveals new intent or emotion (custom extractor prompt). |
| **JSON plan step**       | Usually **no**       | Plans are transient—unless you want world agent to verify an unfinished quest later.                    |

Your Extractor.should_write() prompt can mirror BookWorld’s pattern but add: “Store if the sentence changes relationships, goals, or conveys strong emotion.” Only those get embedded, keeping the DB compact.


### Minimal code snippet

```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# persistent DB per project
client = chromadb.PersistentClient(path="./chroma/chronicles-001")
embedder = OpenAIEmbeddingFunction(model_name="text-embedding-3-small")

collection = client.get_or_create_collection(
    name="chronicles-001",
    embedding_function=embedder,
    metadata={"hnsw:space": "cosine"}       # same config every time
)

def add_memory(txt, meta):
    eid = f"ev_{meta['ts']}"
    vec = embedder([txt])[0]
    collection.add(ids=[eid], embeddings=[vec],
                   documents=[txt], metadatas=[meta])

def retrieve(q_txt, project_id, char_ids, q_mood):
    q_vec = embedder([q_txt])[0]
    where = {"$and": [
        {"project_id": project_id},
        {"character_id": {"$in": char_ids}}
    ]}
    res = collection.query(query_embeddings=[q_vec], n_results=12, where=where)
    # re-rank by mood:
    for r in res["metadatas"][0]:
        emo = r["mood"]; sim = r["distance"]
        r["score"] = sim * (1 + dot(q_mood, emo))
    return sorted(res["metadatas"][0], key=lambda x: -x["score"])[:6]

```

### Operational notes

Concurrency – One client per process/path. Multiple user stories? Spin up separate directories or run Chroma in server mode (docker) so locks don’t clash
Persistence – Chroma writes delta Parquet files; a nightly compaction keeps disk usage sane
Chroma Cookbook
Scaling – For 1-10 M memories, use server mode + HNSW (up to a few GB RAM). If stories exceed that, shard by time or archive closed projects offline.
Cost – All open-source; cloud cost is just the VM/Docker host. Your only paid item is the embedding API (OpenAI/DeepSeek).
Switching later – Because FicWorld talks through a VectorStoreDriver interface, moving to Weaviate or mem0 is swapping one driver file; agent, emotional-RAG, and narrator code remain untouched.