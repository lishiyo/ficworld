# FicWorld Implementation Plan

This document breaks down the FicWorld project into manageable subtasks, providing step-by-step instructions and identifying dependencies to streamline the development process.

---

## Phase 1: Core Project Setup, Data Structures, and Configuration

**Description:** Establish the foundational elements of the project, including directory structure, core data schemas, and configuration loading.
**Dependencies:** None. Essential for all subsequent phases.

### Subtask 1.1: Project Initialization & Directory Structure
- **Instructions:**
    - [x] Initialize a Git repository.
    - [x] Create the main project directory (`ficworld/`).
    - [x] Create subdirectories as defined in `systemPatterns.md`:
        - [ ] `ficworld/data/`
        - [ ] `ficworld/data/roles/`
        - [ ] `ficworld/data/worlds/`
        - [ ] `ficworld/data/prompts/`
        - [ ] `ficworld/presets/`
        - [ ] `ficworld/modules/`
        - [ ] `ficworld/outputs/`
    - [x] Add a `.gitignore` file (e.g., for `__pycache__`, `venv/`, `outputs/*`, `.chroma/` etc.).
    - [x] Set up a virtual environment (e.g., `venv312/`).
    - [ ] Create an initial `requirements.txt` (can be minimal for now).
    - [ ] Create a basic README with install and run instructions.

### Subtask 1.2: Define Core Data Structures (as Python dataclasses or Pydantic models)
- **Instructions:**
    - [ ] Define `MoodVector` (e.g., joy, fear, anger, sadness, surprise, trust floats).
    - [ ] Define `RoleArchetype` (loading from `data/roles/*.json` - includes archetype_name, persona_template, goal_templates, starting_mood_template, activity_coefficient, icon).
    - [ ] Define `WorldDefinition` (loading from `data/worlds/*.json` - includes world_name, description, global_lore, locations, script_beats, world_events_pool).
    - [ ] Define `Preset` (loading from `presets/*.json` - includes world_file, role_files, mode, max_scenes, llm config).
    - [ ] Define `CharacterPlanOutput` (schema for `CharacterAgent.plan()` - action, details, tone_of_action).
    - [ ] Define `WorldState` (e.g., current_scene_id, turn_number, time_of_day, environment_description, active_characters, character_states, recent_events_summary).
    - [ ] Define `MemoryEntry` (timestamp, actor_name, event_description, mood_at_encoding, embedding, significance).
    - [ ] Define `LogEntry` for simulation log (actor, plan, outcome, mood_during_action).

### Subtask 1.3: Implement ConfigLoader Module
- **Instructions:**
    - [ ] Create `modules/config_loader.py`.
    - [ ] Implement function to load a `Preset` JSON file by name (e.g., `load_preset(preset_name)`).
    - [ ] Implement logic within `ConfigLoader` to also load the associated `WorldDefinition` and `RoleArchetype` files specified in the preset.
    - [ ] Ensure paths are handled correctly relative to the project structure.
    - [ ] Add basic error handling (e.g., file not found).

### Subtask 1.4: Initial `main.py` Structure
- **Instructions:**
    - [ ] Create `main.py`.
    - [ ] Add argument parsing for `--preset <preset_name>`.
    - [ ] Use `ConfigLoader` to load the specified preset.
    - [ ] Print loaded configuration (for initial testing).

---

## Phase 2: LLM Interface and Basic Memory Manager (MVP)

**Description:** Implement the interface for interacting with LLMs and a basic in-memory version of the Memory Manager.
**Dependencies:** Phase 1.

### Subtask 2.1: Implement `LLMInterface` Module
- **Instructions:**
    - [ ] Create `modules/llm_interface.py`.
    - [ ] Define a base `LLMInterface` class/functions.
    - [ ] Implement a method to make calls to an LLM provider (e.g., OpenRouter).
        - [ ] Handle API key management (e.g., via environment variables).
        - [ ] Construct requests based on prompt messages (system, user, assistant).
        - [ ] Parse LLM responses.
        - [ ] Include basic error handling and retry logic (optional for MVP).
    - [ ] Support model selection based on preset configuration.

### Subtask 2.2: Implement MVP `MemoryManager` (In-Memory)
- **Instructions:**
    - [ ] Create `modules/memory.py`.
    - [ ] Define `MemoryManager` class.
    - [ ] Implement `remember(actor_name, event_description, mood_at_encoding)`:
        - [ ] Stores a `MemoryEntry` (without embedding for now) in an in-memory list (e.g., `self.ltm_store = []`).
        - [ ] Include timestamp.
    - [ ] Implement `retrieve(actor_name, query_text, current_mood)`:
        - [ ] For MVP: Return all memories for the actor, or last N memories.
        - [ ] (No semantic search or mood-based filtering in this MVP version of retrieve, but design to allow it later).
    - [ ] Implement `summarise_scene(scene_number, scene_log)`:
        - [ ] For MVP: Can be a stub or simply concatenate event descriptions. Actual LLM summarization is a later step.
    - [ ] STM can be handled as part of `WorldState.recent_events_summary` or a simple list in `MemoryManager`.

---

## Phase 3: Character Agent Implementation (Core Logic)

**Description:** Develop the `CharacterAgent` class with its core `reflect` and `plan` methods.
**Dependencies:** Phase 1, Phase 2.

### Subtask 3.1: Define `CharacterAgent` Class
- **Instructions:**
    - [ ] Create `modules/character_agent.py`.
    - [ ] Define `CharacterAgent` class.
    - [ ] Constructor `__init__(self, role_archetype, llm_interface, memory_manager, initial_world_state)`:
        - [ ] Store persona, goals (instantiated from templates if needed), current_mood (from `starting_mood_template`).
        - [ ] Store references to `llm_interface` and `memory_manager`.
        - [ ] Initialize any other character-specific state.

### Subtask 3.2: Implement `reflect()` Method
- **Instructions:**
    - [ ] Define `reflect(self, world_state, relevant_memories)` method.
    - [ ] Prepare the `CHARACTER_REFLECT` prompt using inputs from `world_state`, `relevant_memories`, character's persona, goals, and current mood.
    - [ ] Call `llm_interface.generate_response()` with the prompt.
    - [ ] Parse the LLM's JSON output: `{"updated_mood": {...}, "internal_thought": "..."}`.
    - [ ] Update `self.current_mood` with `updated_mood`.
    - [ ] Return the `updated_mood` and `internal_thought`.
    - [ ] Implement error handling for LLM response parsing.

### Subtask 3.3: Implement `plan()` Method
- **Instructions:**
    - [ ] Define `plan(self, world_state, relevant_memories, internal_thought_summary)` method.
    - [ ] Prepare the `CHARACTER_PLAN` prompt using inputs from `world_state`, `relevant_memories`, `internal_thought_summary`, character's persona, goals, and (updated) current mood.
    - [ ] Call `llm_interface.generate_response()` with the prompt.
    - [ ] Parse the LLM's JSON output (`CharacterPlanOutput` schema).
    - [ ] Return the parsed plan JSON.
    - [ ] Implement error handling for LLM response parsing.

---

## Phase 4: World Agent Implementation

**Description:** Develop the `WorldAgent` to manage the environment, character actions, and events.
**Dependencies:** Phase 1, Phase 3 (for `CharacterPlanOutput` schema).

### Subtask 4.1: Define `WorldAgent` Class
- **Instructions:**
    - [ ] Create `modules/world_agent.py`.
    - [ ] Define `WorldAgent` class.
    - [ ] Constructor `__init__(self, world_definition, llm_interface, characters_data)`:
        - [ ] Initialize `self.world_state` based on `world_definition`.
        - [ ] Store `llm_interface` if `WorldAgent` uses LLM for event generation.
        - [ ] Store character data (names, activity coefficients) for `decide_next_actor`.

### Subtask 4.2: Implement Scene Management Methods
- **Instructions:**
    - [ ] `init_scene(self)`: Sets up initial `world_state` for a new scene.
    - [ ] `judge_scene_end(self, scene_log)`: Determines if a scene should end (e.g., based on turn count, stagnation, or script beats).
    - [ ] `choose_pov_character_for_scene(self, current_world_state)`: Selects POV character for narration.

### Subtask 4.3: Implement Actor and Event Management
- **Instructions:**
    - [ ] `decide_next_actor(self, current_world_state)`: Selects the next `CharacterAgent` to act (e.g., roulette wheel based on activity coefficient). Returns agent object and its current state.
    - [ ] `apply_plan(self, actor_name, plan_json, current_world_state)`:
        - [ ] Validates the feasibility of `plan_json` against `current_world_state`.
        - [ ] (Optional) Modifies plan if necessary.
        - [ ] Updates `current_world_state` based on the plan.
        - [ ] Generates a factual string outcome of the action (e.g., "Sir Rowan moves to the old library."). Returns this outcome.
    - [ ] `should_inject_event(self, current_world_state)`: Logic to decide if a world event should be injected.
    - [ ] `generate_event(self, current_world_state)`:
        - [ ] If LLM-based: Prepares `WORLD_EVENT_GENERATION` prompt, calls LLM, parses output.
        - [ ] If rule-based/scripted: Selects an event from `world_definition.world_events_pool` or script beats.
        - [ ] Returns a factual string outcome of the event.
    - [ ] `update_from_outcome(self, factual_outcome)`: Helper to parse a factual outcome and make necessary changes to `current_world_state`.

---

## Phase 5: Narrator Module Implementation

**Description:** Develop the `Narrator` module to convert simulation logs into prose.
**Dependencies:** Phase 1, Phase 2 (LLM Interface), Phase 4 (for log structure).

### Subtask 5.1: Define `Narrator` Class
- **Instructions:**
    - [ ] Create `modules/narrator.py`.
    - [ ] Define `Narrator` class.
    - [ ] Constructor `__init__(self, llm_interface)`: Stores `llm_interface`.

### Subtask 5.2: Implement `render()` Method
- **Instructions:**
    - [ ] Define `render(self, scene_log, pov_character_name, pov_character_info)` method.
    - [ ] Prepare `NARRATOR_SYSTEM` and `NARRATOR_USER` prompts.
        - [ ] `NARRATOR_USER` will include the `scene_log` (list of factual outcomes), `pov_character_name`, and `pov_character_info` (persona, goals, mood).
    - [ ] Call `llm_interface.generate_response()`.
    - [ ] Return the generated prose string.
    - [ ] Implement error handling.

---

## Phase 6: Simulation Loop Orchestration (`main.py`)

**Description:** Integrate all components to run a full simulation scene by scene.
**Dependencies:** Phase 1, 2, 3, 4, 5.

### Subtask 6.1: Expand `main.py` Logic
- **Instructions:**
    - [ ] Instantiate `ConfigLoader`, `LLMInterface`, `MemoryManager`.
    - [ ] Load preset using `ConfigLoader`.
    - [ ] Instantiate `WorldAgent` using loaded world definition and LLM interface.
    - [ ] Instantiate `CharacterAgent` objects based on loaded role archetypes, LLM interface, and memory manager. Pass them to `WorldAgent` or make them accessible.
    - [ ] Instantiate `Narrator`.
    - [ ] Implement the main simulation loop as per `systemPatterns.md` (Section 7):
        - [ ] Loop through scenes.
        - [ ] `world_agent.init_scene()`.
        - [ ] Inner loop for turns within a scene (`while not world_agent.judge_scene_end(...)`).
            - [ ] `actor_agent, actor_state = world_agent.decide_next_actor(...)`.
            - [ ] `relevant_memories = memory_manager.retrieve(...)`.
            - [ ] `private_reflection_output = actor_agent.reflect(...)`.
            - [ ] Update `actor_state.current_mood` in `world_agent.world_state`.
            - [ ] `plan_json = actor_agent.plan(...)`.
            - [ ] `factual_outcome = world_agent.apply_plan(...)`.
            - [ ] Create `log_entry` and append to `log_for_narrator`.
            - [ ] `world_agent.world_state.update_from_outcome(factual_outcome)`.
            - [ ] `memory_manager.remember(actor_agent, factual_outcome, mood=actor_state.current_mood)`.
            - [ ] Event injection logic: `world_agent.should_inject_event()`, `world_agent.generate_event()`, append to log, update world state.
        - [ ] `pov_character_name, pov_character_info = world_agent.choose_pov_character_for_scene(...)`.
        - [ ] `prose = narrator.render(log_for_narrator, pov_character_name, pov_character_info)`.
        - [ ] Append `prose` to the main story.
        - [ ] `memory_manager.summarise_scene(...)`.
        - [ ] Clear `log_for_narrator`.
    - [ ] Output the final story to `outputs/<preset_name>/story.md`.
    - [ ] (Optional) Output `simulation_log.jsonl`.

---

## Phase 7: Advanced Memory - Vector Store Integration

**Description:** Enhance `MemoryManager` to use a vector database for LTM.
**Dependencies:** Phase 2 (MVP MemoryManager), Phase 6 (working simulation loop for testing).

### Subtask 7.1: Define `VectorStoreDriver` Interface
- **Instructions:**
    - [ ] In `modules/memory.py` (or a new `modules/vector_drivers.py`), define an abstract base class or interface `VectorStoreDriver`.
    - [ ] Specify methods like `add_memory(memory_entry)`, `query_memories(query_embedding, n_results, filter_metadata)`.

### Subtask 7.2: Implement `ChromaVectorStoreDriver`
- **Instructions:**
    - [ ] Implement a concrete class `ChromaVectorStoreDriver(VectorStoreDriver)`.
    - [ ] Integrate `chromadb` library.
    - [ ] Implement embedding generation (using `llm_interface` or a dedicated embedding model utility).
    - [ ] Implement `add_memory`: stores `MemoryEntry` (text as document, embedding, metadata including mood).
    - [ ] Implement `query_memories`: performs semantic search with metadata filtering.
    - [ ] Handle Chroma client initialization and collection management.
    - [ ] Refer to `memory_strategy.md` for schema and query logic.

### Subtask 7.3: Update `MemoryManager` to Use `VectorStoreDriver`
- **Instructions:**
    - [ ] Modify `MemoryManager.__init__` to accept a `vector_store_driver` instance.
    - [ ] Update `MemoryManager.remember` to generate embedding (if not done by driver) and call `driver.add_memory`.
    - [ ] Update `MemoryManager.retrieve` to:
        - [ ] Generate query embedding.
        - [ ] Call `driver.query_memories` to get semantically similar memories.
        - [ ] Implement the Python-side re-ranking logic for Emotional RAG (cosine_sim(query_mood, memory_mood)) as per `memory_strategy.md` and `systemPatterns.md`.
    - [ ] Update `MemoryManager.summarise_scene` to use an LLM via `llm_interface` to generate summaries and store them in LTM.

---

## Phase 8: Script Mode and Beats Implementation

**Description:** Allow the simulation to follow predefined narrative beats.
**Dependencies:** Phase 4 (WorldAgent), Phase 6 (Simulation Loop).

### Subtask 8.1: Enhance `WorldDefinition` and `Preset`
- **Instructions:**
    - [ ] Ensure `WorldDefinition` can load `script_beats` from `worlds/*.json`.
    - [ ] Ensure `Preset` correctly identifies if `mode="script"`.

### Subtask 8.2: Update `WorldAgent` for Script Mode
- **Instructions:**
    - [ ] Modify `WorldAgent.init_scene` to load relevant beats for the current scene if in script mode.
    - [ ] Modify `WorldAgent.judge_scene_end` to consider if all beats for a scene are complete.
    - [ ] Modify `WorldAgent.should_inject_event` and/or `generate_event` to check for triggered events from script beats or to guide event generation based on the current beat's requirements.
    - [ ] `WorldAgent` might need to track the current active beat.

### Subtask 8.3: Update `CharacterAgent` (Optional)
- **Instructions:**
    - [ ] Consider if `CharacterAgent.plan` needs to be aware of the current script beat to guide its actions (e.g., by adding beat description to the prompt context). This could be an advanced refinement.

---

## Phase 9: Testing, Debugging, and Refinement

**Description:** Thoroughly test all integrated components, fix bugs, and refine prompts for better story quality.
**Dependencies:** Phase 1-6 (core functionality). Phase 7-8 if implemented.

### Subtask 9.1: Unit Tests
- **Instructions:**
    - [ ] Write unit tests for individual modules/classes (ConfigLoader, LLMInterface, MemoryManager basic ops, agent methods with mock LLM calls).

### Subtask 9.2: Integration Tests
- **Instructions:**
    - [ ] Test the flow from `main.py` through a single scene with a small number of turns.
    - [ ] Verify data structures are populated and passed correctly.
    - [ ] Check `story.md` and `simulation_log.jsonl` outputs.

### Subtask 9.3: Prompt Engineering & Refinement
- **Instructions:**
    - [ ] Run multiple simulations with different presets.
    - [ ] Analyze LLM outputs for each prompt slot (`CHARACTER_REFLECT`, `CHARACTER_PLAN`, `NARRATOR_USER`, `WORLD_EVENT_GENERATION`).
    - [ ] Iteratively refine prompts in `prompt_design.md` and update their implementation in code to improve:
        - [ ] Character coherence and consistency.
        - [ ] Plan rationality and relevance.
        - [ ] Mood update logic.
        - [ ] Narrative quality (show, don't tell, POV adherence).
        - [ ] Event relevance.

### Subtask 9.4: Bug Fixing
- **Instructions:**
    - [ ] Address any bugs identified during testing.
    - [ ] Pay attention to data flow issues, JSON parsing errors, and logical errors in agent/world interactions.

---

## Phase 10: Stretch Goals (Optional)

**Description:** Implement advanced features based on project priorities.
**Dependencies:** Stable core system (Phases 1-6, 9).

### Subtask 10.1: FastAPI + Gradio UI Server (`server.py`)
- **Instructions:**
    - [ ] Set up a basic FastAPI server.
    - [ ] Create endpoints to:
        - [ ] List available presets.
        - [ ] Start a new simulation run from a preset.
        - [ ] Get status/output of an ongoing/completed run.
    - [ ] Integrate Gradio UI to interact with these endpoints.
    - [ ] (Advanced) Allow live pausing, inspecting agent states, injecting director notes.

### Subtask 10.2: Critic/Editor Agent
- **Instructions:**
    - [ ] Design prompts for a critic agent.
    - [ ] Implement logic for the critic agent to review narrator output or simulation consistency.
    - [ ] Determine how critic feedback is incorporated (e.g., re-prompting narrator, flagging issues).

### Subtask 10.3: Tool-Calling for Agents (e.g., via AutoGen or custom)
- **Instructions:**
    - [ ] Define potential tools (e.g., knowledge lookup, image generation).
    - [ ] Modify `CharacterAgent.plan` or add a new method to support tool use.
    - [ ] Update LLM prompts to instruct agents on how to request tool use.
    - [ ] Implement tool execution logic.

---

This plan provides a structured approach. Subtasks within a phase can often be parallelized. Prioritize completing foundational phases first.
