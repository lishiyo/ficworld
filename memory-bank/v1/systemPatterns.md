# FicWorld V1 Target Architecture Patterns

### 1 Vision & Goal

Evolve the system to generate more realistic and narratively structured stories through enhanced agent autonomy, subjective perspectives, dynamic relationships, parallel character planning, and explicit plot management.

### 2 Guiding Principles (Additions/Refinements for V1)

1.  **Emergence Guided by Structure:** Character autonomy drives moment-to-moment actions within a narrative framework provided by a Plot Manager.
2.  **Subjective Reality:** What each character knows and perceives is filtered; they act based on their *own* view of the world.
3.  **Parallel Cognition, Sequential Action:** Characters can *plan* simultaneously based on the same world state snapshot, but their actions are resolved and executed sequentially by the World Agent.
4.  **Dynamic Relationships:** Character interactions explicitly modify relationship states (trust, affinity, status), influencing future behavior.
5.  **Plot Awareness:** The system tracks progress through a high-level narrative structure (e.g., Acts, Beats) and uses it to guide scene setup, character selection, and pacing.
6.  **(Retained)** Emotion matters, Two layers of thought, Separation of concerns, Config-driven, Model-agnostic, Scalable memory.

### 3 Core Architectural Patterns (V1)

| Pattern                        | Purpose                                                                                                                               | Key Components Involved                                     | Notes                                                                                                                                |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **Simulation Orchestration**   | Manages overall simulation lifecycle, component initialization, and progression through Acts/Scenes.                                     | `SimulationManager`                                         | Evolves from the basic `main.py` loop.                                                                                               |
| **Ground Truth World State**   | Maintains the objective state of the environment, characters, and objects.                                                             | `WorldAgent`                                                | Central repository of facts.                                                                                                         |
| **Subjective Perspective Filter** | Generates a character-specific view of the world state based on their senses, location, memory, and relationships.                  | `PerspectiveFilter`, `WorldAgent`, `MemoryManager`          | Crucial for realistic interaction and preventing omniscience. Can be rule-based initially, LLM-enhanced later.                           |
| **Enhanced Character Model**   | Incorporates deep backstory, explicit goals, and dynamic mood into agent reasoning.                                                     | `CharacterAgent`, `CharacterConfig`                         | Richer character data fuels more nuanced behavior.                                                                                  |
| **Dynamic Relationship Tracking** | Models and updates interpersonal relationships (trust, affinity, status) based on interactions.                                     | `RelationshipManager`, `WorldAgent`, `CharacterAgent`       | Adds social depth and influences character perception and planning.                                                                 |
| **Parallel Planning**          | Allows multiple characters to generate action plans concurrently based on the same state snapshot.                                    | `WorldAgent`, `CharacterAgent`                              | Increases simulation dynamism; requires conflict resolution.                                                                       |
| **Sequential Action Resolution** | Takes multiple proposed plans and determines a coherent sequence of execution, applying outcomes one by one to the ground truth state. | `WorldAgent`                                                | Ensures consistent world state updates despite parallel planning.                                                                   |
| **Plot & Narrative Management**  | Guides the story through predefined structural beats (e.g., Save the Cat) and manages distinct narrative threads (A/B plots).           | `PlotManager`, `WorldAgent`, `SimulationManager`            | Provides high-level narrative direction and influences scene setup, character selection, and pacing.                               |
| **Goal-Driven Behavior**       | Prompts explicitly weigh character goals during planning.                                                                             | `CharacterAgent`                                            | Encourages proactive actions aligned with character motivations.                                                                    |
| **Environmental Interaction**  | Prompts encourage interaction with objects and the environment, not just dialogue.                                                    | `CharacterAgent`, `WorldAgent`                              | Broadens the scope of possible actions.                                                                                             |
| **Memory Partitioning**        | Ensures memory storage and retrieval are specific to each character's experiences (informed by `PerspectiveFilter`).                 | `MemoryManager`, `PerspectiveFilter`                        | Reinforces subjective reality.                                                                                                     |
| **(Retained)**                 | JSON Plan → Verbalise, Inner Monologue, Simulated Emotion, Emotional RAG Memory, Time-weighted Memory, Configurable Presets, LLM Agnostic | `CharacterAgent`, `Narrator`, `MemoryManager`, `LLMInterface` | Foundational patterns remain relevant.                                                                                             |

### 4 High-Level Component Map (V1)

```
SimulationManager (evolved main.py)
 ├─ ConfigLoader
 ├─ WorldAgent
 │   └─ apply_plan()
 ├─ PlotManager          # NEW: Tracks beats, threads, guides WorldAgent
 ├─ PerspectiveFilter    # NEW: Generates subjective views from world_state
 ├─ RelationshipManager  # NEW: Tracks inter-character relationships
 ├─ Narrator
 ├─ MemoryManager        # Now character-partitioned/aware
 ├─ CharacterAgent[N]
 │   ├─ reflect()
 │   └─ plan()
 └─ LLMInterface
```

### 5 Directory Layout, Data Storage, and I/O (Proposed V1)

```
ficworld/
 ├─ data/
 │   ├─ roles/                      # CharacterConfig JSONs (name, persona, backstory, goals)
 │   ├─ worlds/                     # World definition JSONs (environment, locations, lore)
 │   ├─ plot_structures/            # NEW: JSON/YAML files defining narrative structures (e.g., save_the_cat.json)
 │   └─ prompts/                    # Prompt templates
 ├─ presets/                           # Simulation run configurations (preset.json)
 ├─ modules/                           # Core Python logic
 │   ├─ simulation_manager.py     # NEW: Top-level orchestrator
 │   ├─ world_agent.py            # Manages ground truth, turn loop, action resolution
 │   ├─ character_agent.py        # Individual agent logic (reflect, plan)
 │   ├─ narrator.py               # Prose generation
 │   ├─ memory_manager.py         # Character-aware memory storage/retrieval
 │   ├─ llm_interface.py          # LLM API wrapper
 │   ├─ perspective_filter.py     # NEW: Generates subjective world views
 │   ├─ plot_manager.py           # NEW: Manages narrative structure, beats, threads
 │   ├─ relationship_manager.py   # NEW: Tracks relationship states
 │   └─ data_models.py            # NEW: Pydantic/dataclasses for core structures (WorldState, CharacterConfig, etc.)
 ├─ outputs/                           # Generated stories and logs
 │   ├─ <run_name>/
 │   │   ├─ story.md
 │   │   ├─ simulation_log.jsonl    # Includes subjective views, relationship changes?
 │   │   └─ memory_snapshot/        # LTM state
 │   └─ ...
 ├─ main.py                            # Entry point: parses args, initializes SimulationManager
 └─ server.py                        # Optional UI/debugger
```

**Data Flow Overview (V1 Additions):**

1.  **Initialization:** `SimulationManager` loads preset, world, roles, and a `PlotStructure` from `data/plot_structures`. It initializes all components.
2.  **Scene Start:** `SimulationManager` consults `PlotManager` for scene goals based on the current Act/Beat. `PlotManager` suggests relevant characters/threads. `WorldAgent` initializes the scene environment.
3.  **Turn Start:** `WorldAgent`, guided by `PlotManager`, selects multiple characters likely to act.
4.  **Subjective View Generation:** `WorldAgent` gets the ground truth `world_state`. For *each* selected character, it requests a `subjective_world_view` from the `PerspectiveFilter`.
5.  **Parallel Planning:** `WorldAgent` sends the respective `subjective_world_view`, memory context, goal context, and relationship context (from `RelationshipManager`) to each selected `CharacterAgent` *concurrently* to generate `plan_json`s.
6.  **Plan Resolution & Execution:** `WorldAgent` receives multiple plans. It resolves conflicts/dependencies and determines an execution order. It then calls `apply_plan` for *each* action *sequentially*, updating the ground truth `world_state` after each one.
7.  **Outcome Processing:** The `factual_outcome` from `apply_plan` is processed by `PerspectiveFilter` to determine which characters perceived it. Filtered, subjective outcomes are sent to `MemoryManager` for character-specific storage. The outcome also informs `RelationshipManager` to update relevant relationship states.
8.  **Narration:** `Narrator` receives the scene log and POV info (potentially influenced by `PlotManager`) to generate prose.

### 6 Key Data Structures (V1)

```jsonc
// CharacterConfig (e.g., data/roles/knight.json)
{
  "full_name": "Sir Kaelan", // Specific name, not template
  "persona": "A pragmatic veteran knight haunted by past failures...",
  "backstory": "Served in the disastrous Southern campaign, lost his squire...",
  "initial_goals": { // More structured goals
    "long_term": ["Redeem his honor"],
    "short_term": ["Protect the caravan", "Find signs of the Crimson Hand"]
  },
  "activity_coefficient": 0.8,
  "starting_mood": { ... } // As before
}

// WorldState (Ground Truth - managed by WorldAgent)
{
  "current_scene_id": "...",
  "turn_number": 12,
  "time_of_day": "dusk",
  "environment_description": "...",
  "character_states": { // Objective states
    "Sir Kaelan": {"location": "ruined tower", "conditions": ["injured"], "inventory": ["sword"]},
    "Lyra": {"location": "ruined tower", "conditions": [], "inventory": ["healing herbs"]}
  },
  "object_states": {
    "tower_door": {"state": "barricaded"}
  },
  "recent_objective_events": ["Lyra applied herbs to Kaelan's wound.", "Sounds of shouting outside."]
}

// SubjectiveWorldView (Generated by PerspectiveFilter for a character)
// Example for Sir Kaelan, injured and maybe distrustful
{
  "perceived_location": "ruined tower (dimly lit)",
  "visible_characters": {
    "Lyra": {"estimated_condition": ["focused"], "apparent_mood": "calm"} // Kaelan might misinterpret
  },
  "visible_objects": {
    "tower_door": {"state": "barricaded"}
  },
  "recent_perceived_events": ["Lyra touched my wound.", "Shouting outside."], // Filtered events
  "inferred_context": "Potential danger outside. Lyra seems trustworthy... for now." // Filter adds interpretation
}

// RelationshipState (Managed by RelationshipManager)
// Example: {(char_a, char_b): state}
{
  ("Sir Kaelan", "Lyra"): {"trust": 0.6, "affinity": 0.3, "status": "allies_of_necessity"},
  ("Sir Kaelan", "Bandit Leader"): {"trust": 0.0, "affinity": -0.8, "status": "enemies"}
}

// NarrativeThread (Managed by PlotManager)
{
  "thread_id": "main_quest_artifact",
  "name": "Recover the Sunstone",
  "status": "active",
  "involved_characters": ["Sir Kaelan", "Lyra"],
  "associated_beats": ["setup", "catalyst", "fun_and_games", ...],
  "summary": "Kaelan and Lyra must retrieve the Sunstone from the bandits."
}

// PlotStructure (Example: data/plot_structures/my_epic_adventure.json)
// This file defines the overarching narrative beats and acts.
{
  "plot_name": "The Quest for the Emberstone",
  "description": "A three-act adventure to find a legendary artifact.",
  "acts": [
    {
      "act_id": "act_1_the_call",
      "name": "Act I: The Call to Adventure",
      "beats": [
        {
          "beat_id": "beat_1_ordinary_world",
          "name": "An Ordinary Day",
          "description": "Introduce the protagonist in their normal setting. Establish the status quo.",
          "narrative_goals": ["Establish protagonist's daily life", "Hint at an unfulfilled desire or problem"],
          "key_characters": ["Protagonist"],
          "setting_suggestions": ["Protagonist's village/home"]
        },
        {
          "beat_id": "beat_2_inciting_incident",
          "name": "The Catalyst",
          "description": "An event occurs that disrupts the protagonist's life and presents a challenge or goal.",
          "narrative_goals": ["Disrupt status quo", "Present the main quest/problem"],
          "triggers_event_type": "major_disruption"
        },
        {
          "beat_id": "beat_3_refusal_or_acceptance",
          "name": "The Choice",
          "description": "The protagonist initially hesitates or eagerly accepts the call.",
          "narrative_goals": ["Show protagonist's internal conflict/decision process"]
        }
      ]
    },
    {
      "act_id": "act_2_the_journey",
      "name": "Act II: Trials and Tribulations",
      "beats": [
        {
          "beat_id": "beat_4_new_allies_enemies",
          "name": "Meeting the Crew",
          "description": "Protagonist gathers allies and encounters initial adversaries.",
          "narrative_goals": ["Introduce key supporting characters and antagonists", "First test of protagonist's resolve"]
        }
        // ... more beats for Act II ...
      ]
    },
    {
      "act_id": "act_3_the_climax",
      "name": "Act III: Resolution",
      "beats": [
        // ... beats for Act III ...
        {
          "beat_id": "beat_final_confrontation",
          "name": "Final Showdown",
          "description": "The protagonist faces the main antagonist or ultimate challenge.",
          "narrative_goals": ["Resolve main conflict"]
        }
      ]
    }
  ]
}

// Preset Configuration (e.g., presets/my_adventure_preset.json)
// Note the `plot_structure_file` key
{
  "preset_name": "My Epic Emberstone Adventure",
  "world_file": "data/worlds/generic_fantasy_world.json",
  "role_files": [
    "data/roles/brave_hero.json",
    "data/roles/wise_mentor.json",
    "data/roles/scheming_villain.json"
  ],
  "plot_structure_file": "data/plot_structures/my_epic_adventure.json", // <-- Links to the plot structure
  "max_scenes_per_beat": 5, // Example of a new config for plot manager
  "llm": "deepseek/deepseek-r1:free"
}

// Memory Entry (Structure remains similar, but input is subjective)
{
  "timestamp": "scene_3_turn_12",
  "actor_name": "Sir Kaelan", // Character whose memory this is
  "subjective_event": "Lyra seemed hesitant when treating my wound.", // Stored based on filtered perception
  "mood_at_encoding": {"joy":0.0,"fear":0.4,"anger":0.1,"sadness":0.2,"surprise":0.1,"trust":0.4}, // Kaelan's mood
  "embedding": [...],
  "significance": 0.6
}
```

### 7 Simulation Loop (Conceptual V1 with Parallel Planning)

```python
# In SimulationManager
plot_manager.load_structure("save_the_cat.json")

for act in plot_manager.get_acts():
    for beat in plot_manager.get_beats_for_act(act):
        plot_manager.set_current_beat(beat)
        
        # PlotManager guides scene setup (relevant location, characters for this beat/thread)
        scene_config = plot_manager.get_scene_config_for_beat(beat)
        world_agent.init_scene(scene_config)
        
        log_for_narrator = []
        while not plot_manager.judge_scene_end(beat, world_agent.get_world_state()):
            # WorldAgent, guided by PlotManager, selects multiple characters based on beat/threads
            active_character_ids = world_agent.decide_active_characters_for_turn(plot_manager.get_guidance())
            
            ground_truth_state = world_agent.get_world_state()
            plans = {}
            subjective_views = {}

            # --- Parallel Phase ---
            # 1. Get Subjective Views Concurrently
            for char_id in active_character_ids:
                # Assumes perspective filter access memory implicitly or explicitly passed
                subjective_views[char_id] = perspective_filter.get_view_for(char_id, ground_truth_state) 

            # 2. Get Plans Concurrently
            for char_id in active_character_ids:
                agent = character_agents[char_id]
                memory_context = memory_manager.retrieve(char_id, ...)
                relationship_context = relationship_manager.get_context_for(char_id)
                goal_context = agent.get_active_goals()
                
                # Run reflect/plan potentially (needs async/threading)
                plans[char_id] = agent.plan(subjective_views[char_id], memory_context, relationship_context, goal_context) 
            # --- End Parallel Phase ---

            # 3. Resolve and Execute Sequentially
            ordered_actions = world_agent.resolve_and_sequence_plans(plans) # List of (char_id, action_details)

            for char_id, action_details in ordered_actions:
                # apply_plan uses ground_truth_state and updates it
                factual_outcome = world_agent.apply_plan(char_id, action_details) 
                
                # Log objective outcome (or filtered for narrator?)
                log_for_narrator.append(...)
                
                # Update relationships based on outcome
                relationship_manager.update_relationships(factual_outcome, involved_chars=[char_id, ...])

                # Filter outcome and store subjective memory
                observed_by = perspective_filter.get_observers(factual_outcome, ground_truth_state)
                for observer_id in observed_by:
                    subjective_outcome = perspective_filter.get_subjective_event(observer_id, factual_outcome)
                    memory_manager.remember(observer_id, subjective_outcome, world_agent.get_character_state(observer_id).current_mood)

            # Inject world events guided by PlotManager?
            # ...

        # Narration uses log + POV guided by PlotManager
        pov_info = plot_manager.choose_pov_for_scene(beat, world_agent.get_world_state())
        prose = narrator.render(log_for_narrator, pov_info)
        # ... save story, summarize scene memory etc. ...
```

### 8 Prompt Slots (V1 - Key Changes)

*   **CHARACTER_SYSTEM:** Needs to incorporate richer `backstory`, structured `initial_goals`. Relationship summaries might be added dynamically.
*   **CHARACTER_REFLECT:** Input context now includes `subjective_world_view` (not ground truth). Prompt needs to leverage `backstory`, `goals`, and `relationship_context`.
*   **CHARACTER_PLAN:** Input context includes `subjective_world_view`, `relationship_context`, `goal_context`. Prompt needs to explicitly encourage goal-driven planning and environmental interaction, respecting subjective view.
*   **PERSPECTIVE_FILTER (LLM-based variant):** Needs prompts to infer what a character would perceive/know given ground truth, their state, memory, and relationships.
*   **PLOT_MANAGER (LLM-based variant):** Might need prompts to assess scene progress against beat goals, suggest relevant characters, or choose POV based on narrative structure.
*   **RELATIONSHIP_MANAGER (LLM-based variant):** Might need prompts to update trust/affinity based on textual descriptions of interactions.
*   **(Existing Prompts):** `WORLD_*` prompts may need adjustment if guided by `PlotManager`. `NARRATOR_*` prompts remain similar but receive POV guidance.

### 9 Memory Strategy v1 (Refinements)

*   **Input Filtering:** `MemoryManager.remember` *must* receive the *subjective* event description filtered by `PerspectiveFilter` for the specific character.
*   **Retrieval Context:** Queries to `MemoryManager.retrieve` should also be informed by the character's current goals and relationships, potentially adding more context vectors to the retrieval process beyond just semantic content and mood.
*   **Scene Summaries:** Still valuable for long-term context, provided to characters via their subjective view or memory context.

*(Sections 10-12 on LLM/Config, Stretch Goals, Milestones would be adapted based on the new V1 scope)*

---

**Outcome V1:** A system capable of generating stories with more believable characters acting on subjective information within a structured narrative, featuring dynamic relationships and more complex interactions.
