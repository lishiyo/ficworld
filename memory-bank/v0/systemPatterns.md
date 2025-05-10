# AgentVerse MVP

### 1  Vision & Goal

Build a system that can generate coherent short stories → full novels **through emergent interaction of autonomous character agents with emotion, private reasoning, and memory**.

We take BookWorld’s proven design (role agents + world agent + narrator) and adapt it for a lean, easily‑swappable Python stack running on OpenRouter models (default: DeepSeek R1).

### 2  Guiding Principles

1. **Emergence first** – characters decide; the world nudges.
2. **Emotion matters** – every agent carries a live mood vector that biases memory retrieval and tone.
3. **Two layers of thought** – private chain‑of‑thought (hidden) → public action/dialogue.
4. **Separation of concerns** – simulation log ≠ narrative prose.
5. **Config‑driven** – every run described by a single preset JSON.
6. **Model‑agnostic** – swap LLMs via one config flag.
7. **Scalable memory** – time‑weighted retrieval with optional vector store.

### 3  Core Architectural Patterns (borrowed / adapted from BookWorld)

| Pattern                     | Purpose                                                                                                                      | BookWorld ref               | Adaptation                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------ |
| **JSON Plan → Verbalise**   | Agent’s first pass returns structured action (`{"action":"speak", "text": …}`), second pass/via narrator turns it into prose | `RPAgent.plan()`            | `CharacterAgent.plan()` returns JSON; narrator/world chooses what to verbalise.      |
| **Inner Monologue** | hidden reasoning step; fuels emotion & plan | Generative Agents | first pass: `reflect()` – produces private thought + mood update (not logged); second pass: `plan()` |
| **Simulated Emotion** | mood vector drives tone & memory keys | Emotional RAG 2024 | fields: {joy, fear, anger, sadness, surprise, trust} ∈ [0‑1].
| **Emotional RAG Memory** | retrieve memories with matching emotional context | Emotional RAG | `MemoryManager.retrieve(query, mood)` weights cosine_sim × mood_sim. |
| **World Agent as Director** | Picks speaker, injects events, ends scene | `WorldAgent.*`              | `WorldAgent` keeps `decide_next_actor`, `generate_event`, `judge_scene_end` prompts. |
| **Time‑weighted Memory**    | Keeps recent yet important memories | `memory.py`                 | `MemoryManager` with decay weight w = 𝛼 · (age)⁻¹  (configurable).  Combine with Emotional RAG keys.                |
| **Scene Stagnation Guard**  | Auto‑advance if chat stalls     | `judge_if_ended()`          | Hard stop if ≤ Δtokens change in N turns, else force event.                          |
| **Activity Coefficient**    | Spotlight control per role | `role.json["activity"]`     | `activity` weights roulette selection of next actor.                                 |
| **Preset JSON**             | Reproducible experiments              | `experiment_presets/*.json` | `presets/` holds world/roles/script; CLI: `python main.py --preset mystery_forest`.  |
| **Free vs Script Mode**     | Emergent vs outline‑guided          | BookWorld `mode`            | `mode="free" / "script"`; script beats fed to world agent as hints.                  |

### 4  High‑Level Component Map

```
main.py
 ├─ ConfigLoader         # reads preset
 ├─ WorldAgent           # env + director logic
 ├─ Narrator             # log → prose (show, don’t tell, limited POV)
 ├─ CharacterAgent[N]    # persona, goals, memory, plan()
 |    ├─ reflect()       # inner monologue, mood update
 │    └─ plan()          # JSON action
 ├─ MemoryManager        # time‑weighted FAISS (optional in‑RAM list)
 └─ LLMInterface         # OpenRouter wrapper (model swap)
```

### 5  Directory Layout

```
agentverse/
 ├─ data/
 │   ├─ roles/          # per‑character JSON
 │   ├─ worlds/         # location graph, lore
 │   └─ prompts/        # *.txt templates (en, zh …)
 ├─ presets/
 │   └─ demo_forest.json
 ├─ modules/
 │   ├─ character_agent.py
 │   ├─ world_agent.py
 │   ├─ narrator.py
 │   ├─ memory.py
 │   └─ llm_interface.py
 ├─ main.py
 └─ server.py           # optional FastAPI/Gradio debugger
```

### 6  Key Data Structures

```jsonc
// roles/knight.json (example)
{
  "name": "Sir Rowan",
  "persona": "Stoic border‑knight …",
  "goals": ["escort the scholar to safety"],
  "activity": 0.8,
  "starting_mood": {"joy":0.2,"fear":0.1,"anger":0.0,
                     "sadness":0.1,"surprise":0.0,"trust":0.6}
}

// presets/demo_forest.json
{
  "world_file": "worlds/haunted_forest.json",
  "role_files": ["roles/knight.json", "roles/scholar.json",
                 "roles/rogue.json", "roles/spirit.json"],
  "mode": "free",
  "max_scenes": 5,
  "llm": "deepseek/deepseek-r1:free"
}
```

### 7  Simulation Loop (pseudo‑code)

```python
for scene in range(cfg.max_scenes):
    world_agent.init_scene()
    while not world_agent.judge_scene_end(log):
        actor = world_agent.decide_next_actor(state)
        private = actor.reflect(world_state, memory)      # hidden
        plan    = actor.plan(world_state, memory, private)
        outcome = world_agent.apply(plan)
        log.append(outcome)
        memory.remember(actor, outcome, mood=actor.mood)
        if world_agent.should_inject_event():
            event = world_agent.generate_event(state)
            log.append(event)
    prose = narrator.render(log, pov=world_agent.choose_pov())
    story.append(prose)
    memory.summarise_scene(scene, log)
    log.clear()
```

### 8  Prompt Slots

* **CHARACTER_SYSTEM:** persona · goals · mood · memory summary
* **CHARACTER_REFLECT:** “Think silently: how do you feel, what do you secretly want, adjust your mood vector (JSON). Do NOT reveal in story.”
* **CHARACTER_PLAN:** env summary · last N exchanges → “Return a JSON plan influenced by your mood”.
* **WORLD_SYSTEM:** director rules.
* **NARRATOR\_SYSTEM:** style guide (show/don’t tell, POV, tense).
* **NARRATOR\_USER:** raw log list → “Rewrite as coherent prose paragraph(s)”.

### 9  Memory Strategy v1

* **STM (per agent):** last k turns (k configurable).
* **LTM:** Time‑weighted retriever (FAISS) → top m memories merged back into prompt. Each memory stored with embedding + mood vector.
* **Retrieval:** cosine(sim_event, sim_query) × (1 + mood_dot).
* **Compression:** every M scenes, narrator autowrites a chapter summary; old logs pruned once summarised.

### 10  LLM & Config

```toml
[llm]
provider   = "openrouter"
model_name = "deepseek/deepseek-r1:free"
max_tokens = 4096
router_url = "https://openrouter.ai/api/v1"
```

Swap model by editing this block or passing `--model` CLI flag.

### 11  Stretch Goals

* **Critic/Editor agent** for consistency checks.
* **Tool‑calling** via AutoGen to fetch knowledge or images.
* **Parallel timelines** (multi‑world‑state fork manager) for stories like *Anxiety Is the Dizziness of Freedom*.
* **FastAPI + Gradio** UI for live pausing, editing, or injecting director notes.

### 12  Milestones

1. **MVP loop** – 4 characters, 1 scene, narrator output ✔
2. Preset loader + activity coefficient + stagnation guard.
3. Time‑weighted memory + scene summaries.
4. Script mode with outline hints.
5. Long‑form test (\~5k words) & swap to CAMEL memory backend.

---

**Outcome:** a lean, preset‑driven story engine inspired by BookWorld, architected for rapid experimentation, model flexibility, and incremental depth.
