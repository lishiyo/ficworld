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
    - [x] Create an initial `requirements.txt` (can be minimal for now).
    - [x] Create a basic README with install and run instructions.

### Subtask 1.2: Define Core Data Structures (as Python dataclasses or Pydantic models)
- **Instructions:**
    - [x] Define `MoodVector` (e.g., joy, fear, anger, sadness, surprise, trust floats).
    - [x] Define `RoleArchetype` (loading from `data/roles/*.json` - includes archetype_name, persona_template, goal_templates, starting_mood_template, activity_coefficient, icon).
    - [x] Define `WorldDefinition` (loading from `data/worlds/*.json` - includes world_name, description, global_lore, locations, script_beats, world_events_pool).
    - [x] Define `Preset` (loading from `presets/*.json` - includes world_file, role_files, mode, max_scenes, llm config).
    - [x] Define `CharacterPlanOutput` (schema for `CharacterAgent.plan()` - action, details, tone_of_action).
    - [x] Define `WorldState` (e.g., current_scene_id, turn_number, time_of_day, environment_description, active_characters, character_states, recent_events_summary).
    - [x] Define `MemoryEntry` (timestamp, actor_name, event_description, mood_at_encoding, embedding, significance).
    - [x] Define `LogEntry` for simulation log (actor, plan, outcome, mood_during_action).
    - [x] Write unit tests for data structure instantiation, default values, and any helper methods (e.g., `RoleArchetype.to_mood_vector()`).

### Subtask 1.3: Implement ConfigLoader Module
- **Instructions:**
    - [x] Create `modules/config_loader.py`.
    - [x] Implement function to load a `Preset` JSON file by name (e.g., `load_preset(preset_name)`).
    - [x] Implement logic within `ConfigLoader` to also load the associated `WorldDefinition` and `RoleArchetype` files specified in the preset.
    - [x] Ensure paths are handled correctly relative to the project structure.
    - [x] Add basic error handling (e.g., file not found).
    - [x] Write unit tests for `ConfigLoader` to verify correct loading and parsing of preset, world, and role JSON files, including handling of file not found and invalid JSON errors.

### Subtask 1.4: Initial `main.py` Structure
- **Instructions:**
    - [x] Create `main.py`.
    - [x] Add argument parsing for `--preset <preset_name>`.
    - [x] Use `ConfigLoader` to load the specified preset.
    - [x] Print loaded configuration (for initial testing).
    - [x] Write basic integration tests for `main.py` argument parsing and successful configuration loading via `ConfigLoader` (mocking file system if necessary).

---

## Phase 2: LLM Interface and Basic Memory Manager (MVP)

**Description:** Implement the interface for interacting with LLMs and a basic in-memory version of the Memory Manager.
**Dependencies:** Phase 1.

### Subtask 2.1: Implement `LLMInterface` Module
- **Instructions:**
    - [x] Create `modules/llm_interface.py`.
    - [x] Define a base `LLMInterface` class/functions.
    - [x] Implement a method to make calls to an LLM provider (e.g., OpenRouter).
        - [x] Handle API key management (e.g., via environment variables, using `OPENROUTER_API_KEY`).
        - [x] Construct requests based on prompt messages (system, user, assistant).
        - [x] Parse LLM responses.
        - [x] Include basic error handling and retry logic (optional for MVP).
    - [x] Support model selection based on preset configuration.
    - [x] Write unit tests for `LLMInterface` (mocking `httpx` calls) to verify correct request construction, API key handling, and response parsing for both text and JSON modes. Test error handling for API issues.

### Subtask 2.2: Implement MVP `MemoryManager` (In-Memory)
- **Instructions:**
    - [x] Create `modules/memory.py`.
    - [x] Define `MemoryManager` class.
    - [x] Implement `remember(actor_name, event_description, mood_at_encoding)`:
        - [x] Stores a `MemoryEntry` (without embedding for now) in an in-memory list (e.g., `self.ltm_store = []`).
        - [x] Include timestamp.
    - [x] Implement `retrieve(actor_name, query_text, current_mood)`:
        - [x] For MVP: Return all memories for the actor, or last N memories.
        - [x] (No semantic search or mood-based filtering in this MVP version of retrieve, but design to allow it later).
    - [x] Implement `summarise_scene(scene_number, scene_log)`:
        - [x] For MVP: Can be a stub or simply concatenate event descriptions. Actual LLM summarization is a later step.
    - [x] STM can be handled as part of `WorldState.recent_events_summary` or a simple list in `MemoryManager`.
    - [x] Write unit tests for `MemoryManager` methods (`remember`, `retrieve`, `summarise_scene` MVP, `clear_stm`, `reset_memory`) to ensure correct in-memory data manipulation.

---

## Phase 3: Character Agent Implementation (Core Logic)

**Description:** Develop the `CharacterAgent` class with its core `reflect` and `plan` methods.
**Dependencies:** Phase 1, Phase 2.

### Subtask 3.1: Define `CharacterAgent` Class
- **Instructions:**
    - [x] Create `modules/character_agent.py`.
    - [x] Define `CharacterAgent` class.
    - [x] Constructor `__init__(self, role_archetype, llm_interface, memory_manager, initial_world_state)`:
        - [x] Store persona, goals (instantiated from templates if needed), current_mood (from `starting_mood_template`).
        - [x] Store references to `llm_interface` and `memory_manager`.
        - [x] Initialize any other character-specific state.
    - [x] Write unit tests for `CharacterAgent.__init__` to ensure correct initialization of persona, goals, mood, and references to dependencies.

### Subtask 3.2: Implement `reflect()` Method
- **Instructions:**
    - [x] Define `reflect(self, world_state, relevant_memories)` method.
    - [x] Prepare the `CHARACTER_REFLECT` prompt using inputs from `world_state`, `relevant_memories`, character's persona, goals, and current mood.
    - [x] Call `llm_interface.generate_response()` with the prompt.
    - [x] Parse the LLM's JSON output: `{"updated_mood": {...}, "internal_thought": "..."}`.
    - [x] Update `self.current_mood` with `updated_mood`.
    - [x] Return the `updated_mood` and `internal_thought`.
    - [x] Implement error handling for LLM response parsing.
    - [x] Write unit tests for `reflect()` (mocking `llm_interface`) to verify correct prompt preparation, LLM call, parsing of JSON response, mood update, and return values. Test error handling for LLM response issues.

### Subtask 3.3: Implement `plan()` Method
- **Instructions:**
    - [x] Define `plan(self, world_state, relevant_memories, internal_thought_summary)` method.
    - [x] Prepare the `CHARACTER_PLAN` prompt using inputs from `world_state`, `relevant_memories`, `internal_thought_summary`, character's persona, goals, and (updated) current mood.
    - [x] Call `llm_interface.generate_response()` with the prompt.
    - [x] Parse the LLM's JSON output (`CharacterPlanOutput` schema).
    - [x] Return the parsed plan JSON.
    - [x] Implement error handling for LLM response parsing.
    - [x] Write unit tests for `plan()` (mocking `llm_interface`) to verify correct prompt preparation, LLM call, parsing of `CharacterPlanOutput` JSON, and return values. Test error handling for LLM response issues.

---

## Phase 4: World Agent Implementation

**Description:** Develop the `WorldAgent` to manage the environment, character actions, and events.
**Dependencies:** Phase 1, Phase 3 (for `CharacterPlanOutput` schema).

### Subtask 4.1: Define `WorldAgent` Class
- **Instructions:**
    - [x] Create `modules/world_agent.py`.
    - [x] Define `WorldAgent` class.
    - [x] Constructor `__init__(self, world_definition, llm_interface, characters_data, ...)`:
        - [x] Initialize `self.world_state` based on `world_definition`.
        - [x] Store `llm_interface` if `WorldAgent` uses LLM for event generation.
        - [x] Store character data (names, activity coefficients) for `decide_next_actor`.
        - [x] Store configurable thresholds (max_turns, stagnation, event injection chances, history limits).
    - [x] Write unit tests for `WorldAgent.__init__` to verify correct initialization of world state and storage of dependencies and configurable parameters.

### Subtask 4.2: Implement Scene Management Methods
- **Instructions:**
    - [x] `init_scene(self)`: Sets up initial `world_state` for a new scene.
    - [x] `judge_scene_end(self, scene_log)`: Determines if a scene should end (LLM-driven, with script mode and fallback heuristics).
    - [x] `choose_pov_character_for_scene(self, current_world_state)`: Selects POV character for narration (LLM-driven, with fallback).
    - [x] Write unit tests for `init_scene`, `judge_scene_end` (with various log inputs and LLM mocks), and `choose_pov_character_for_scene` (with LLM mocks and fallbacks) to ensure correct scene flow logic.

### Subtask 4.3: Implement Actor and Event Management
- **Instructions:**
    - [x] `decide_next_actor(self, current_world_state)`: Selects the next `CharacterAgent` to act (LLM-driven, with script mode and activity coefficient fallback).
    - [x] `apply_plan(self, actor_name, plan_json, current_world_state)`:
        - [x] Uses LLM to interpret `plan_json` in context of `current_world_state`.
        - [x] Generates a factual string outcome of the action. Returns this outcome.
    - [x] `should_inject_event(self, current_world_state)`: Logic to decide if a world event should be injected (LLM-driven, with script mode and fallback heuristics).
    - [x] `generate_event(self, current_world_state)`:
        - [x] If LLM-based: Prepares `WORLD_EVENT_GENERATION` prompt, calls LLM, parses output.
        - [x] If rule-based/scripted: Selects an event from `world_definition.world_events_pool` or script beats.
        - [x] Returns a factual string outcome of the event.
    - [x] `update_from_outcome(self, factual_outcome)`: Helper to parse a factual outcome (using LLM to extract structured changes like location, conditions, time) and make necessary changes to `current_world_state`.
    - [x] Write unit tests for `decide_next_actor` (LLM mocks, script mode, fallback).
    - [x] Write unit tests for `apply_plan` (LLM mocks for outcome generation).
    - [x] Write unit tests for `should_inject_event` and `generate_event` (LLM mocks, script mode, rule-based selection, fallback).
    - [x] Write unit tests for `update_from_outcome` (LLM mocks for structured data extraction and state updates).

---

## Phase 5: Narrator Module Implementation

**Description:** Develop the `Narrator` module to convert simulation logs into prose.
**Dependencies:** Phase 1, Phase 2 (LLM Interface), Phase 4 (for log structure).

### Subtask 5.1: Define `Narrator` Class
- **Instructions:**
    - [x] Create `modules/narrator.py`.
    - [x] Define `Narrator` class.
    - [x] Constructor `__init__(self, llm_interface)`: Stores `llm_interface`.
    - [x] Write unit tests for `Narrator.__init__` to verify dependency storage.

### Subtask 5.2: Implement `render()` Method
- **Instructions:**
    - [x] Define `render(self, scene_log, pov_character_name, pov_character_info)` method.
    - [x] Prepare `NARRATOR_SYSTEM` and `NARRATOR_USER` prompts.
        - [x] `NARRATOR_USER` will include the `scene_log` (list of factual outcomes), `pov_character_name`, and `pov_character_info` (persona, goals, mood).
    - [x] Call `llm_interface.generate_response()` (now `generate_response_sync`).
    - [x] Return the generated prose string.
    - [x] Implement error handling.
    - [x] Write unit tests for `render()` (mocking `llm_interface`) to verify correct prompt preparation (system and user with scene log and POV info) and LLM call. Test error handling.

---

## Phase 6: Simulation Loop Orchestration (`main.py`)

**Description:** Integrate all components to run a full simulation scene by scene.
**Dependencies:** Phase 1, 2, 3, 4, 5.

### Subtask 6.1: Expand `main.py` Logic
- **Instructions:**
    - [x] Instantiate `ConfigLoader`, `LLMInterface`, `MemoryManager`.
    - [x] Load preset using `ConfigLoader`.
    - [x] Instantiate `WorldAgent` using loaded world definition and LLM interface.
    - [x] Instantiate `CharacterAgent` objects based on loaded role archetypes, LLM interface, and memory manager. Pass them to `WorldAgent` or make them accessible.
    - [x] Instantiate `Narrator`.
    - [x] Implement the main simulation loop as per `systemPatterns.md` (Section 7):
        - [x] Loop through scenes.
        - [x] `world_agent.init_scene()`.
        - [x] Inner loop for turns within a scene (`while not world_agent.judge_scene_end(...)`).
            - [x] `actor_agent, actor_state = world_agent.decide_next_actor(...)`.
            - [x] `relevant_memories = memory_manager.retrieve(...)`.
            - [x] `private_reflection_output = actor_agent.reflect(...)`.
            - [x] Update `actor_state.current_mood` in `world_agent.world_state`.
            - [x] `plan_json = actor_agent.plan(...)`.
            - [x] `factual_outcome = world_agent.apply_plan(...)`.
            - [x] Create `log_entry` and append to `log_for_narrator`.
            - [x] `world_agent.world_state.update_from_outcome(factual_outcome)`.
            - [x] `memory_manager.remember(actor_agent, factual_outcome, mood=actor_state.current_mood)`.
            - [x] Event injection logic: `world_agent.should_inject_event()`, `world_agent.generate_event()`, append to log, update world state.
        - [x] `pov_character_name, pov_character_info = world_agent.choose_pov_character_for_scene(...)`.
        - [x] `prose = narrator.render(log_for_narrator, pov_character_name, pov_character_info)`.
        - [x] Append `prose` to the main story.
        - [x] `memory_manager.summarise_scene(...)`.
        - [x] Clear `log_for_narrator`.
    - [x] Output the final story to `outputs/<preset_name>/story.md`.
    - [x] (Optional) Output `simulation_log.jsonl`.
    - [x] Develop integration tests that run a minimal end-to-end simulation for one or two turns, verifying component interactions and basic output generation (mocking LLM calls to control variability and cost).

---

## Phase 7: Improvements to Story Gen

See [story_loop.md](./story_loop.md) for how this system is CURRENTLY working.

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
    - [ ] Write unit tests for `WorldAgent` methods affected by script mode, verifying correct loading of beats, scene ending logic based on beats, and event generation/injection based on script requirements.

### Subtask 8.3: Update `CharacterAgent` (Optional)
- **Instructions:**
    - [ ] Consider if `CharacterAgent.plan` needs to be aware of the current script beat to guide its actions (e.g., by adding beat description to the prompt context). This could be an advanced refinement.
    - [ ] If implemented, write unit tests for `CharacterAgent.plan` to verify it correctly incorporates script beat information into its context and decision-making (mocking LLM).

---

## Phase 9: Testing, Debugging, and Refinement

**Description:** Thoroughly test all integrated components, fix bugs, and refine prompts for better story quality.
**Dependencies:** Phase 1-6 (core functionality). Phase 8 if implemented.

### Subtask 9.1: Unit Tests
- **Instructions:**
    - [ ] Review and ensure comprehensive unit test coverage for all modules.
    - [ ] Address any remaining test warnings (e.g., async test issues in `test_character_agent.py`).

### Subtask 9.2: Integration Tests
- **Instructions:**
    - [ ] Expand integration tests for `main.py` to cover multiple scenes and turns.
    - [ ] Test interactions between `CharacterAgent`, `WorldAgent`, `MemoryManager`, and `Narrator`.
    - [ ] Verify data flow, state updates, and log generation across components.
    - [ ] Test both "free" and "script" modes with sample presets.

### Subtask 9.3: Prompt Engineering & Refinement
- **Instructions:**
    - [ ] Run multiple simulations with different presets.
    - [ ] Analyze LLM outputs for each prompt slot (`CHARACTER_REFLECT`, `CHARACTER_PLAN`, `NARRATOR_USER`, `WORLD_AGENT` methods).
    - [ ] Iteratively refine prompts in `prompt_design.md` and update their implementation in code to improve:
        - [ ] Character coherence and consistency.
        - [ ] Plan rationality and relevance.
        - [ ] Mood update logic.
        - [ ] Narrative quality (show, don't tell, POV adherence).
        - [ ] Event relevance and impact.
        - [ ] World state parsing from outcomes.

### Subtask 9.4: Bug Fixing and Performance
- **Instructions:**
    - [ ] Address any bugs identified during integration testing.
    - [ ] Pay attention to data flow issues, JSON parsing errors, and logical errors in agent/world interactions.
    - [ ] Profile simulation runs and identify any performance bottlenecks (optional for MVP but good to keep in mind).

---

## Phase 10: Advanced Memory - Vector Store Integration

**Description:** Enhance `MemoryManager` to use a vector database for LTM.
**Dependencies:** Phase 2 (MVP MemoryManager), Phase 6 (working simulation loop for testing), Phase 9 (stable system).

### Subtask 10.1: Define `VectorStoreDriver` Interface
- **Instructions:**
    - [ ] In `modules/memory.py` (or a new `modules/vector_drivers.py`), define an abstract base class or interface `VectorStoreDriver`.
    - [ ] Specify methods like `add_memory(memory_entry)`, `query_memories(query_embedding, n_results, filter_metadata)`.

### Subtask 10.2: Implement `ChromaVectorStoreDriver`
- **Instructions:**
    - [ ] Implement a concrete class `ChromaVectorStoreDriver(VectorStoreDriver)`.
    - [ ] Integrate `chromadb` library.
    - [ ] Implement embedding generation (using `llm_interface` or a dedicated embedding model utility).
    - [ ] Implement `add_memory`: stores `MemoryEntry` (text as document, embedding, metadata including mood).
    - [ ] Implement `query_memories`: performs semantic search with metadata filtering.
    - [ ] Handle Chroma client initialization and collection management.
    - [ ] Refer to `memory_strategy.md` for schema and query logic.
    - [ ] Write unit tests for `ChromaVectorStoreDriver` (mocking `chromadb` client if actual DB operations are slow/complex for unit tests, or using an ephemeral in-memory Chroma instance) to verify embedding generation, memory addition, and querying with metadata filters.

### Subtask 10.3: Update `MemoryManager` to Use `VectorStoreDriver`
- **Instructions:**
    - [ ] Modify `MemoryManager.__init__` to accept a `vector_store_driver` instance.
    - [ ] Update `MemoryManager.remember` to generate embedding (if not done by driver) and call `driver.add_memory`.
    - [ ] Update `MemoryManager.retrieve` to:
        - [ ] Generate query embedding.
        - [ ] Call `driver.query_memories` to get semantically similar memories.
        - [ ] Implement the Python-side re-ranking logic for Emotional RAG (cosine_sim(query_mood, memory_mood)) as per `memory_strategy.md` and `systemPatterns.md`.
    - [ ] Update `MemoryManager.summarise_scene` to use an LLM via `llm_interface` to generate summaries and store them in LTM.
    - [ ] Write unit tests for the updated `MemoryManager` methods, focusing on the interaction with the `VectorStoreDriver` (mocking the driver). Test the Emotional RAG re-ranking logic.
    - [ ] Write unit tests for LLM-based `summarise_scene` in `MemoryManager` (mocking `llm_interface`).

---

## Phase 11: Stretch Goals

**Description:** Implement advanced features based on project priorities.
**Dependencies:** Stable core system (Phases 1-6, 8, 9, 7).

### Subtask 11.1: FastAPI + Gradio UI Server (`server.py`)
- **Instructions:**
    - [ ] Set up a basic FastAPI server.
    - [ ] Create endpoints to:
        - [ ] List available presets.
        - [ ] Start a new simulation run from a preset.
        - [ ] Get status/output of an ongoing/completed run.
    - [ ] Integrate Gradio UI to interact with these endpoints.
    - [ ] (Advanced) Allow live pausing, inspecting agent states, injecting director notes.

### Subtask 11.2: Critic/Editor Agent
- **Instructions:**
    - [ ] Design prompts for a critic agent.
    - [ ] Implement logic for the critic agent to review narrator output or simulation consistency.
    - [ ] Determine how critic feedback is incorporated (e.g., re-prompting narrator, flagging issues).

### Subtask 11.3: Tool-Calling for Agents (e.g., via AutoGen or custom)
- **Instructions:**
    - [ ] Define potential tools (e.g., knowledge lookup, image generation).
    - [ ] Modify `CharacterAgent.plan` or add a new method to support tool use.
    - [ ] Update LLM prompts to instruct agents on how to request tool use.
    - [ ] Implement tool execution logic.

---

This plan provides a structured approach. Subtasks within a phase can often be parallelized. Prioritize completing foundational phases first.
