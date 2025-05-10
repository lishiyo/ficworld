# FicWorld MVP

### 1  Vision & Goal

Build a system that can generate coherent short stories → full novels **through emergent interaction of autonomous character agents with emotion, private reasoning, and memory**.

We take BookWorld's proven design (role agents + world agent + narrator) and adapt it for a lean, easily‑swappable Python stack running on OpenRouter models (default: DeepSeek R1).

### 2  Guiding Principles

1. **Emergence first** – characters decide; the world nudges.
2. **Emotion matters** – every agent carries a live mood vector that biases memory retrieval and tone.
3. **Two layers of thought** – private chain‑of‑thought (hidden) → public action/dialogue.
4. **Separation of concerns** – simulation log ≠ narrative prose.
5. **Config‑driven** – every run described by a single preset JSON.
6. **Model‑agnostic** – swap LLMs via one config flag.
7. **Scalable memory** – time‑weighted retrieval with optional vector store.

### 3  Core Architectural Patterns (borrowed / adapted from BookWorld)

| Pattern                     | Purpose                                                                                                                      | BookWorld ref               | Adaptation                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------ |
| **JSON Plan → Verbalise**   | Agent's first pass returns structured action (e.g., `{"action":"speak", "details": {"text": "Hello!"}, "tone_of_action": "friendly"}`), second pass/via narrator turns it into prose | `RPAgent.plan()`            | `CharacterAgent.plan()` returns JSON; `WorldAgent` applies it, Narrator verbalises outcome. |
| **Inner Monologue** | hidden reasoning step; fuels emotion & plan | Generative Agents | `CharacterAgent.reflect()` produces private thought string + updated mood vector (JSON). This output feeds into `CharacterAgent.plan()`. |
| **Simulated Emotion** | mood vector drives tone & memory keys | Emotional RAG 2024 | fields: {joy, fear, anger, sadness, surprise, trust} ∈ [0‑1]. Updated in `reflect()`. |
| **Emotional RAG Memory** | retrieve memories with matching emotional context | Emotional RAG | `MemoryManager.retrieve(query, current_mood)` weights cosine_sim(query, memory_embedding) × cosine_sim(current_mood, memory_mood). |
| **World Agent as Director** | Picks speaker, injects events, ends scene | `WorldAgent.*`              | `WorldAgent` keeps `decide_next_actor`, `generate_event`, `judge_scene_end` prompts. |
| **Time‑weighted Memory**    | Keeps recent yet important memories | `memory.py`                 | `MemoryManager` with decay weight w = 𝛼 · (age)⁻¹  (configurable).  Combine with Emotional RAG keys.                |
| **Scene Stagnation Guard**  | Auto‑advance if chat stalls     | `judge_if_ended()`          | Hard stop if ≤ Δtokens change in N turns, else force event.                          |
| **Activity Coefficient**    | Spotlight control per role | `role.json["activity"]`     | `activity` weights roulette selection of next actor.                                 |
| **Preset JSON**             | Reproducible experiments              | `experiment_presets/*.json` | `presets/` holds world/roles/script; CLI: `python main.py --preset mystery_forest`.  |
| **Free vs Script Mode**     | Emergent vs outline‑guided          | BookWorld `mode`            | `mode="free" / "script"`; script beats fed to world agent as hints.                  |

### 4  High‑Level Component Map

```
main.py
 ├─ ConfigLoader         # reads preset
 ├─ WorldAgent           # env + director logic. Manages world_state, applies character plans, injects events.
 │    └─ apply_plan()    # validates plan, updates world_state, generates factual outcome string.
 ├─ Narrator             # log of factual outcomes + POV char info → prose (show, don't tell, limited POV)
 ├─ CharacterAgent[N]    # persona, goals, memory
 │    ├─ reflect(world_state, observations) # private thought (string) & mood update (JSON output)
 │    └─ plan(world_state, observations, private_reflection_summary) # JSON action plan (output)
 ├─ MemoryManager        # time‑weighted FAISS (optional in‑RAM list). Stores memories with mood.
 │    ├─ remember(actor, event_outcome, mood_at_event)
 │    └─ retrieve(actor, query, current_mood)
 └─ LLMInterface         # OpenRouter wrapper (model swap)
```

### 5  Directory Layout, Data Storage, and I/O

This section details how data is organized, stored, and processed within FicWorld.

```
ficworld/
 ├─ data/                               # Input data: world definitions, character archetypes, prompt templates
 │   ├─ roles/                      # JSON files, one per character archetype (e.g., knight.json, scholar.json)
 │   │   └─ knight.json             # Example: {"name_template": "Sir {Name}", "persona": "...", ...}
 │   ├─ worlds/                     # JSON files defining settings, locations, lore, optional event beats for script mode
 │   │   └─ haunted_forest.json     # Example: {"name": "Haunted Forest", "description": "...", "locations": [...], "script_beats": [...]}
 │   └─ prompts/                    # Text files for base prompt segments (e.g., narrator_style.txt)
 ├─ presets/                           # Input data: JSON files defining specific simulation runs
 │   └─ demo_forest_run.json        # Combines a world, specific roles, mode, llm, etc.
 ├─ modules/                           # Core Python logic for agents, narrator, memory, etc.
 │   ├─ character_agent.py
 │   ├─ world_agent.py
 │   ├─ narrator.py
 │   ├─ memory.py                 # Handles STM (in-memory lists) & LTM (e.g., FAISS/vector store on disk if enabled)
 │   └─ llm_interface.py
 ├─ outputs/                           # Generated stories and logs from simulation runs
 │   ├─ demo_forest_run/            # Directory named after the preset used
 │   │   ├─ story.md                # Final narrated story output
 │   │   ├─ simulation_log.jsonl    # Detailed turn-by-turn log (JSONL format)
 │   │   └─ memory_snapshot/        # Optional: LTM state if persisted (e.g., FAISS index files)
 │   └─ ...                         # Other run outputs
 ├─ main.py                            # Main simulation script, orchestrates the components
 └─ server.py                        # Optional FastAPI/Gradio debugger and live interaction UI
```

**Data Flow Overview:**

1.  **Inputs (User-defined):**
    *   `presets/*.json`: The primary input specified by the user (e.g., via CLI `python main.py --preset demo_forest_run`). This file dictates:
        *   Which `worlds/*.json` file to load for environment, lore, and potentially scripted beats.
        *   Which `roles/*.json` files to use for character archetypes.
        *   Simulation parameters like `mode` ("free" or "script"), `max_scenes`, chosen `llm`.
    *   `data/worlds/*.json`: Contains the description of the game world, including locations, key objects, and overall environmental context. Can also include pre-defined story beats if `mode="script"`.
    *   `data/roles/*.json`: Defines character archetypes with personas, typical goals, starting mood templates, and activity coefficients. Actual character instances in a run will be generated from these.
    *   `data/prompts/*.txt`: (Optional) Base templates for parts of prompts, which can be loaded and formatted by the LLMInterface or agent classes.

2.  **Runtime Data (In-Memory & Potentially Persisted):**
    *   **World State:** Managed by `WorldAgent`. A Python dictionary or object holding the current state of the simulation environment (e.g., scene ID, turn number, time, character locations, active characters with their states including current mood). This is dynamic and updated every turn. Not typically persisted unless for save/resume functionality (stretch goal).
    *   **Character Agent State:** Each `CharacterAgent` instance maintains its specific persona, goals (can evolve), current mood vector (dynamic), and references to its memories.
    *   **Short-Term Memory (STM):** Typically held in memory by each agent or the `MemoryManager`. Consists of recent events, observations, and outcomes (e.g., last K turns). Cleared or summarized periodically.
    *   **Long-Term Memory (LTM):** Managed by `MemoryManager`. Stores significant events, reflections, and summaries with their emotional context and semantic embeddings. Can be an in-memory list for simple runs or backed by a vector store (e.g., FAISS, ChromaDB) on disk, especially for longer stories or if persistence between sessions is needed. If disk-based, these files would reside under `outputs/<run_name>/memory_snapshot/`.
    *   **Simulation Log:** A detailed log of all actions, reflections (if chosen to be logged, typically not the full private thought), plans, outcomes, and world events. Accumulated in memory during a scene and used by the Narrator. A version of this might be written to `outputs/<run_name>/simulation_log.jsonl`.

3.  **Outputs (Generated by FicWorld):**
    *   `outputs/<run_name>/story.md`: The final, human-readable narrative prose generated by the Narrator module, typically in Markdown format.
    *   `outputs/<run_name>/simulation_log.jsonl`: A machine-readable, detailed log of the simulation. Each line is a JSON object representing a turn or significant event, including actor, action, mood, outcome, etc. Useful for debugging, analysis, and fine-tuning.
    *   `outputs/<run_name>/memory_snapshot/`: (If LTM is persisted) Files related to the LTM state, like vector store indexes or serialized memory objects.

**Key Data Structures in `roles/*.json` and `worlds/*.json`:**

*   `roles/character_archetype.json`:
    ```json
    {
      "archetype_name": "Resourceful Scholar",
      "persona_template": "A knowledgeable but physically frail scholar, always curious... Speaks with precise language.",
      "goal_templates": [
        "Discover the ancient secret of {lore_topic}.",
        "Survive the current perilous situation."
      ],
      "starting_mood_template": {"joy":0.3, "fear":0.4, "anger":0.1, "sadness":0.2, "surprise":0.5, "trust":0.6},
      "activity_coefficient": 0.7, // Relative likelihood to be chosen as next actor
      "icon": "📚"
    }
    ```
*   `worlds/world_definition.json`:
    ```json
    {
      "world_name": "The Whispering Peaks",
      "description": "A range of mist-shrouded mountains, rumored to hold ancient ruins and strange creatures.",
      "global_lore": {
        "magic_system": "Magic is rare and based on elemental energies.",
        "key_factions": [{"name": "Mountain Clans", "details": "..."}]
      },
      "locations": [
        {"id": "base_camp", "name": "Base Camp", "description": "A small, fortified camp at the foot of the peaks.", "connections": ["peak_trail"]},
        {"id": "peak_trail", "name": "Treacherous Peak Trail", "description": "A narrow path winding up the mountainside.", "connections": ["base_camp", "ruined_shrine"]}
      ],
      "script_beats": [ // Optional: for 'script' mode
        {"scene_id": 1, "beat_id": "discovery", "description": "Characters find a strange map at Base Camp.", "triggers_event": "map_found_event"},
        {"scene_id": 2, "beat_id": "ambush", "description": "An ambush occurs on the Peak Trail.", "required_location": "peak_trail"}
      ],
      "world_events_pool": [ // Optional: for 'free' mode random events or triggered events
        {"event_id": "sudden_storm", "description": "A fierce blizzard suddenly rolls in.", "effects": ["visibility_reduced"]}
      ]
    }
    ```

This expanded section should provide a clearer picture of how data is structured and flows through the FicWorld system.

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
  "mode": "free", // "free" or "script" (script uses beats from world_file or a dedicated script_file)
  "max_scenes": 5,
  "llm": "deepseek/deepseek-r1:free"
}

// CharacterAgent.plan() output example
{
  "action": "speak", // e.g., "speak", "move", "interact_object", "attack"
  "details": { // content varies by action type
    "text": "We must find shelter before nightfall.", // for "speak"
    "target_location": "old_ruins", // for "move"
    "object_name": "locked_chest", // for "interact_object"
    "target_character": "Goblin" // for "attack"
  },
  "tone_of_action": "urgent" // e.g., "cautious", "angry", "joyful", "determined"
}

// World State example (simplified)
// Maintained by WorldAgent, passed to agents as needed
{
  "current_scene_id": "scene_1_forest_encounter",
  "turn_number": 5,
  "time_of_day": "late afternoon",
  "environment_description": "A dense, shadowy forest. A narrow path winds ahead.",
  "active_characters": ["Sir Rowan", "Scholar Elara"],
  "character_states": {
    "Sir Rowan": {
      "location": "forest path",
      "current_mood": {"joy":0.1,"fear":0.3,"anger":0.1,"sadness":0.1,"surprise":0.2,"trust":0.5},
      "conditions": ["weary"]
    },
    "Scholar Elara": {
      "location": "forest path",
      "current_mood": {"joy":0.1,"fear":0.5,"anger":0.0,"sadness":0.2,"surprise":0.3,"trust":0.3},
      "conditions": ["frightened"]
    }
  },
  "recent_events_summary": ["A wolf howled nearby.", "Sir Rowan drew his sword."]
}

// Memory Entry example (in MemoryManager)
{
  "timestamp": "scene_1_turn_4",
  "actor_name": "Sir Rowan",
  "event_description": "Sir Rowan drew his sword after hearing a wolf howl.", // Factual outcome from WorldAgent
  "mood_at_encoding": {"joy":0.1,"fear":0.4,"anger":0.1,"sadness":0.1,"surprise":0.3,"trust":0.4},
  "embedding": [0.123, -0.456, ...], // Semantic embedding of event_description
  "significance": 0.7 // Optional, for more advanced retrieval
}
```

### 7  Simulation Loop (pseudo‑code)

```python
for scene in range(cfg.max_scenes):
    world_agent.init_scene()
    log_for_narrator = []
    while not world_agent.judge_scene_end(log_for_narrator): // Log contains factual outcomes
        actor_agent, actor_state = world_agent.decide_next_actor(current_world_state)
        
        // Retrieve relevant memories for reflection and planning
        relevant_memories = memory.retrieve(actor_agent, query="current situation assessment", current_mood=actor_state.current_mood)
        
        private_reflection_output = actor_agent.reflect(current_world_state, relevant_memories)
        # private_reflection_output = {"updated_mood": {...}, "internal_thought": "..."}
        actor_state.current_mood = private_reflection_output["updated_mood"] # Update mood in world_state

        plan_json = actor_agent.plan(current_world_state, relevant_memories, private_reflection_output["internal_thought"])
        
        factual_outcome = world_agent.apply_plan(actor_agent.name, plan_json, current_world_state)
        # factual_outcome is a string like "Sir Rowan moved to the old library."

        log_entry = {
            "actor": actor_agent.name, 
            "plan": plan_json, 
            "outcome": factual_outcome, 
            "mood_during_action": actor_state.current_mood 
        }
        log_for_narrator.append(log_entry)
        current_world_state.update_from_outcome(factual_outcome) // WorldAgent updates its state

        memory.remember(actor_agent, factual_outcome, mood=actor_state.current_mood)
        
        if world_agent.should_inject_event(current_world_state):
            event_outcome = world_agent.generate_event(current_world_state)
            log_for_narrator.append({"actor": "World", "outcome": event_outcome})
            current_world_state.update_from_outcome(event_outcome)

    pov_character_name, pov_character_info = world_agent.choose_pov_character_for_scene(current_world_state)
    # pov_character_info might include persona, goals, current_mood for richer narration
    prose = narrator.render(log_for_narrator, pov_character_name, pov_character_info)
    story.append(prose)
    memory.summarise_scene(scene, log_for_narrator) // Create a compressed memory of the scene
    log_for_narrator.clear()
```

### 8  Prompt Slots

See [prompt_design](./prompt_design.md) for details on these prompts:

* **CHARACTER_SYSTEM:** persona · goals · current_mood (dynamic) · summary of key memories/world_state relevant to character.
* **CHARACTER_REFLECT:** Input: current world_state summary, recent observations/outcomes. Prompt: "Think silently: how do you feel about [recent events]? What are your secret thoughts, desires, or fears given your persona [persona] and goals [goals]? Based on this, provide an updated mood vector as JSON `{"joy":0.1, ...}` and a brief internal thought string `{"internal_thought": "..."}`. Do NOT reveal this internal thought or specific mood reasoning in any public actions.
* **CHARACTER_PLAN:** Input: env summary · last N exchanges/outcomes · current_mood (from reflect) · internal_thought (from reflect). Prompt: "Return a JSON plan for your public action, following schema `{"action":"type", "details":{...}, "tone_of_action":"mood_string"}`. Your action should be influenced by your mood and private thoughts.
* **WORLD_SYSTEM:** director rules, overall plot outline (if in "script" mode), rules for event generation.
* **WORLD_EVENT_GENERATION (if LLM-based):** Input: current world_state, recent story events. Prompt: "Given the current story progression, generate a concise, neutral, factual description of a new environmental detail or minor event. Output as a simple string."
* **NARRATOR_SYSTEM:** style guide (show/don't tell, POV, tense, desired literary style).
* **NARRATOR_USER:** Input: raw log list of factual outcomes (from `log_for_narrator`), POV character name, POV character info (persona, goals, mood). Prompt: "Rewrite as coherent prose paragraph(s) from [POV_character_name]'s limited perspective, drawing on their persona and mood.

### 9  Memory Strategy v1

See [memory_strategy.md](./memory_strategy.md) for detail.

* **STM (per agent):** Last k turns' factual outcomes (k configurable), readily available in `world_state.recent_events_summary` or similar.
* **LTM (MemoryManager):** Time‑weighted retriever (see [memory_strategy.md](./memory_strategy.md)) → top m memories merged into prompt context for `reflect` and `plan`.
    *   **Memory Entry Structure:** `{"timestamp": "scene_X_turn_Y", "actor_name": str, "event_description": str, "mood_at_encoding": {"joy":..., ...}, "embedding": [...], "significance": float}`
* **Retrieval:** `score = (w_semantic * semantic_sim(query_emb, memory_emb)) + (w_emotional * cosine_sim(current_mood_vec, memory_mood_vec))`. Weights `w_semantic` and `w_emotional` are configurable.
* **Compression:** Every M scenes or at chapter breaks, `MemoryManager.summarise_scene()` (potentially using Narrator or a dedicated summarization LLM call) creates a condensed summary of the scene. Old, detailed log entries from that scene can be down-weighted or archived once this summary is stored in LTM (itself with an averaged/dominant mood).

### 10  LLM & Config

```toml
[llm]
provider   = "openrouter"
model_name = "deepseek/deepseek-r1:free"
max_tokens = 4096
router_url = "https://openrouter.ai/api/v1"
```

Swap model by editing this block or passing `--model` CLI flag.

### 11  Stretch Goals

* **Critic/Editor agent** for consistency checks.
* **Tool‑calling** via AutoGen to fetch knowledge or images.
* **Parallel timelines** (multi‑world‑state fork manager) for stories like *Anxiety Is the Dizziness of Freedom*.
* **FastAPI + Gradio** UI for live pausing, editing, or injecting director notes.

### 12  Milestones

1. **MVP loop** – 4 characters, 1 scene, narrator output ✔
2. Preset loader + activity coefficient + stagnation guard.
3. Time‑weighted memory + scene summaries.
4. Script mode with outline hints.
5. Long‑form test (\~5k words) & swap to CAMEL memory backend.

---

**Outcome:** a lean, preset‑driven story engine inspired by BookWorld, architected for rapid experimentation, model flexibility, and incremental depth.
