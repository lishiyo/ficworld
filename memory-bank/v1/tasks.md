# FicWorld V1 Implementation Plan

This plan outlines the subtasks for implementing the V1 architecture, integrating improvements into the original workflow. It prioritizes building the necessary V1 foundations before completing all original phases.

**Assumption:** Original Phases 1-6 (Core Setup, LLM, Memory MVP, Character Agent, World Agent, Narrator, Basic Loop) are functionally complete as prerequisites.

---

## Phase 7: V1 Improvements - Part 1 (Highly Feasible & Feasible Foundations)

**Description:** Implement core V1 enhancements related to character depth, action variety, relationships, and basic memory improvements.
**Dependencies:** Original Phases 1-6.

### Subtask 7.1: Enhance Character Data & Loading
- **Instructions:**
    - [ ] Update `RoleArchetype` data model (or create new `CharacterConfig`) in `modules/data_models.py` to include `full_name`, `backstory`, and structured `initial_goals` (long-term, short-term).
    - [ ] Update `data/roles/` JSON files to reflect the new structure (provide examples).
    - [ ] Modify `ConfigLoader` to load this enhanced character configuration.
    - [ ] Update `CharacterAgent.__init__` to store and utilize `full_name`, `backstory`, and structured `goals`.
    - [ ] Write/update unit tests for data models, `ConfigLoader`, and `CharacterAgent.__init__`.

### Subtask 7.2: Enhance Agent Prompts (Core V1 Focus)
- **Instructions:**
    - [ ] Update `CHARACTER_SYSTEM` prompt to include `full_name`, `backstory`, and `initial_goals`.
    - [ ] Update `CHARACTER_REFLECT` prompt:
        - [ ] Ensure it utilizes backstory, goals.
    - [ ] Update `CHARACTER_PLAN` prompt:
        - [ ] Ensure it utilizes backstory, goals.
        - [ ] **Action Variety:** Explicitly instruct the LLM to consider a wider range of actions (movement, interaction, non-action, environmental) beyond just "speak".
        - [ ] **Goal-Driven:** Explicitly instruct the LLM to weigh character goals heavily when deciding on a plan.
        - [ ] **Environmental Interaction:** Explicitly instruct the LLM to consider interacting with objects/environment mentioned in the world state.
    - [ ] Update `Narrator` Prompts:
        - [ ] Modify `NARRATOR_SYSTEM` or add a parameter to `render` to accept and use an `AUTHOR_STYLE` string (e.g., loaded from preset or env).
    - [ ] Write/update unit tests for prompt generation logic within agents (mocking LLM).

### Subtask 7.3: Implement Relationship Manager (Basic)
- **Instructions:**
    - [ ] Create `modules/relationship_manager.py`.
    - [ ] Define `RelationshipManager` class.
    - [ ] Define `RelationshipState` data structure (e.g., dictionary mapping (char_a, char_b) tuples to state dict `{'trust': float, 'affinity': float, 'status': str}`).
    - [ ] Implement `__init__` to initialize empty relationship states.
    - [ ] Implement `get_state(char_a, char_b)` to retrieve the relationship state.
    - [ ] Implement `update_state(char_a, char_b, new_state)` or `adjust_state(char_a, char_b, trust_delta, affinity_delta, new_status)` method.
    - [ ] Implement `get_context_for(character_id)` to generate a summary string of a character's relationships for prompt injection.
    - [ ] Write unit tests for `RelationshipManager` methods.

### Subtask 7.4: Integrate Relationships & Summaries into Agents
- **Instructions:**
    - [ ] Modify `SimulationManager` (or `main.py`) to instantiate `RelationshipManager`.
    - [ ] Modify `WorldAgent`:
        - [ ] Add logic to call `RelationshipManager.update_state` based on interaction outcomes (`factual_outcome` from `apply_plan`). This might require an LLM call within `apply_plan` or a dedicated step to interpret the outcome's social implications.
    - [ ] Modify `CharacterAgent`:
        - [ ] Update `reflect` and `plan` methods to accept `relationship_context` (from `RelationshipManager.get_context_for`) and `scene_summary_context` (from `MemoryManager`).
        - [ ] Incorporate these contexts into the `CHARACTER_REFLECT` and `CHARACTER_PLAN` prompts.
    - [ ] Modify `MemoryManager`:
        - [ ] Ensure `summarise_scene` is functional (even if basic).
        - [ ] Implement a method like `get_recent_scene_summaries()` to provide context.
    - [ ] Write/update unit tests for the modified methods in `WorldAgent`, `CharacterAgent`, and `MemoryManager`, focusing on the integration points (mocking dependencies).

---

## Phase 7 (Continued): V1 Improvements - Part 2 (Subjectivity & Memory)

**Description:** Implement the core mechanisms for subjective perception and memory.
**Dependencies:** Phase 7 - Part 1.

### Subtask 7.5: Define Subjective Data Structures
- **Instructions:**
    - [ ] Define `SubjectiveWorldView` data model in `modules/data_models.py` (include perceived location, visible characters/objects with potentially inferred states, perceived events, inferred context).
    - [ ] Define `SubjectiveEvent` data model (representing a character's filtered perception of an objective `FactualOutcome`).

### Subtask 7.6: Implement Perspective Filter Module
- **Instructions:**
    - [ ] Create `modules/perspective_filter.py`.
    - [ ] Define `PerspectiveFilter` class.
    - [ ] Implement `get_view_for(self, character_id, ground_truth_world_state, memory_manager)`:
        - [ ] Takes the objective `world_state`.
        - [ ] Filters based on character's location, senses (start simple, e.g., same location = visible), known facts (requires `memory_manager` access).
        - [ ] Can use rules initially (e.g., line-of-sight). LLM enhancement is optional later.
        - [ ] Constructs and returns a `SubjectiveWorldView` instance.
    - [ ] Implement `get_observers(self, factual_outcome, ground_truth_world_state)`:
        - [ ] Determines which characters likely perceived the objective `factual_outcome`. Returns a list of character IDs.
    - [ ] Implement `get_subjective_event(self, observer_id, factual_outcome, ground_truth_world_state)`:
        - [ ] Generates the `SubjectiveEvent` data for a specific observer based on the objective outcome and their likely perception filters (e.g., hearing vs seeing).
    - [ ] Write unit tests for `PerspectiveFilter` methods (mocking memory access if needed). Test different scenarios (character locations, obstacles, event types).

### Subtask 7.7: Refactor WorldAgent for Ground Truth
- **Instructions:**
    - [ ] Ensure `WorldAgent` exclusively manages the objective `ground_truth_world_state`.
    - [ ] Modify methods like `apply_plan` and `update_from_outcome` to *only* update this ground truth state.
    - [ ] Remove any direct passing of potentially objective state to `CharacterAgent` if it bypasses the filter.
    - [ ] Update `WorldAgent`'s turn loop (placeholder for Phase 9 parallel changes):
        - [ ] Get ground truth state.
        - [ ] For the selected actor: Call `PerspectiveFilter.get_view_for`.
        - [ ] Pass the *subjective view* to `actor_agent.reflect` and `actor_agent.plan`.
        - [ ] After `apply_plan` generates `factual_outcome`:
            - [ ] Call `PerspectiveFilter.get_observers`.
            - [ ] For each observer, call `PerspectiveFilter.get_subjective_event`.
            - [ ] Call `MemoryManager.remember` with the observer's ID and their `SubjectiveEvent`.
    - [ ] Write/update unit tests for `WorldAgent` focusing on state management and interaction with `PerspectiveFilter`.

### Subtask 7.8: Update CharacterAgent for Subjectivity
- **Instructions:**
    - [ ] Modify `CharacterAgent.reflect` and `CharacterAgent.plan` methods to accept `subjective_world_view` as input instead of the potentially objective state.
    - [ ] Ensure prompts (`CHARACTER_REFLECT`, `CHARACTER_PLAN`) are updated to clearly state that the provided context is the character's *own perspective*.
    - [ ] Write/update unit tests for `CharacterAgent` methods focusing on using the `SubjectiveWorldView` input.

### Subtask 7.9: Update MemoryManager for Subjectivity
- **Instructions:**
    - [ ] Modify `MemoryManager.remember` method signature to accept `character_id` and `subjective_event` data.
    - [ ] Ensure memory entries store the *subjective* event description/data.
    - [ ] Ensure retrieval (`MemoryManager.retrieve`) operates on these subjective memories for the given character.
    - [ ] Write/update unit tests for `MemoryManager.remember` and `retrieve` focusing on character partitioning and storing/retrieving subjective data.

---

## Phase 8: Plot Management & Beats (V1 Narrative Structure)

**Description:** Implement the Plot Manager and integrate narrative structure (Acts, Beats, Threads).
**Dependencies:** Phase 7 (Core V1 Foundations).

### Subtask 8.1: Define Plot Data Structures & Config
- **Instructions:**
    - [ ] Define `PlotStructure` data model in `modules/data_models.py` (Acts, Beats, goals).
    - [ ] Define `NarrativeThread` data model (ID, name, characters, status, summary, associated beats).
    - [ ] Create `data/plot_structures/` directory.
    - [ ] Create example plot structure JSON/YAML files (e.g., `save_the_cat.json`). If you want to set the beats yourself, then add your own plot structure file here.
    - [ ] Update `Preset` data model to include a `plot_structure_file` field.
    - [ ] Update `ConfigLoader` to load the specified `PlotStructure`.
    - [ ] Write unit tests for plot data models and `ConfigLoader` updates.

### Subtask 8.2: Implement Plot Manager Module
- **Instructions:**
    - [ ] Create `modules/plot_manager.py`.
    - [ ] Define `PlotManager` class.
    - [ ] Implement `__init__(self, plot_structure)` to load and store the narrative structure.
    - [ ] Implement methods to manage state: `set_current_beat`, `get_current_beat`, `advance_beat`, `start_thread`, `end_thread`, `assign_character_to_thread`, etc.
    - [ ] Implement `get_scene_config_for_beat(self, beat)` to suggest characters, location, goals for `WorldAgent.init_scene`.
    - [ ] Implement `get_guidance(self)` to provide context (current beat goals, active threads) for `WorldAgent.decide_active_characters_for_turn`.
    - [ ] Implement `judge_scene_end(self, beat, world_state)` to assess if beat objectives are met (potentially requires LLM).
    - [ ] Implement `choose_pov_for_scene(self, beat, world_state)` to select POV based on beat/thread relevance.
    - [ ] Write unit tests for `PlotManager` methods (mocking LLM if used for judging).

### Subtask 8.3: Implement Simulation Manager
- **Instructions:**
    - [ ] Create `modules/simulation_manager.py`.
    - [ ] Define `SimulationManager` class.
    - [ ] `__init__`: Takes loaded config (preset, world, roles, plot structure), instantiates all core components (`WorldAgent`, `CharacterAgents`, `MemoryManager`, `Narrator`, `PerspectiveFilter`, `RelationshipManager`, `PlotManager`, `LLMInterface`).
    - [ ] Implement `run_simulation()`:
        - [ ] Contains the top-level loop (Acts, Beats) driven by `PlotManager`.
        - [ ] Calls `PlotManager` to get scene configurations.
        - [ ] Calls `WorldAgent.run_scene()` (refactored from `main.py` loop) passing necessary context (e.g., beat goals).
        - [ ] Coordinates narration after each scene.
        - [ ] Handles saving outputs.
    - [ ] Refactor `main.py` to be a simple entry point that initializes `SimulationManager` and calls `run_simulation()`.
    - [ ] Write unit tests for `SimulationManager` initialization and the main `run_simulation` loop structure (mocking component interactions).

### Subtask 8.4: Integrate Plot Manager with World Agent
- **Instructions:**
    - [ ] Modify `WorldAgent.__init__` to accept `PlotManager` instance.
    - [ ] Modify `WorldAgent.init_scene` to use `PlotManager.get_scene_config_for_beat`.
    - [ ] Modify `WorldAgent.decide_active_characters_for_turn` (placeholder for parallel planning) to use `PlotManager.get_guidance`.
    - [ ] Modify the scene ending logic within `WorldAgent.run_scene` (or `SimulationManager`) to use `PlotManager.judge_scene_end`.
    - [ ] Modify POV selection logic to use `PlotManager.choose_pov_for_scene`.
    - [ ] Write/update unit tests for `WorldAgent` focusing on integration with `PlotManager` (mocking `PlotManager`).

### Subtask 8.5: Develop Offline Story Parser Utility (Deferred/Optional)
- **Instructions:**
    - [ ] Plan a separate script (`tools/parse_story.py`?).
    - [ ] Use LLMs to parse input story text.
    - [ ] Extract characters, relationships, plot points, setting.
    - [ ] Generate draft JSON files for `roles`, `world`, `plot_structure`.
    - [ ] This is a utility, not core runtime, can be developed later.

---

## Phase 9: V1 Improvements - Parallel Planning

**Description:** Refactor the turn loop to support concurrent plan generation and sequential resolution.
**Dependencies:** Phase 7 (Core V1 Foundations).

### Subtask 9.1: Refactor WorldAgent Turn Logic
- **Instructions:**
    - [ ] Identify the core turn loop within `WorldAgent` (or potentially moved to `SimulationManager` and called by it).
    - [ ] Modify `decide_active_characters_for_turn` to return a *list* of character IDs.
    - [ ] Implement concurrent/parallel execution for:
        - [ ] Calling `PerspectiveFilter.get_view_for` for each active character.
        - [ ] Calling `CharacterAgent.plan` for each active character using their respective subjective views. (Requires agents/methods to be thread-safe or use appropriate async/concurrency patterns).
    - [ ] Implement `resolve_and_sequence_plans(self, plans_dict)`:
        - [ ] Takes dictionary `{char_id: plan_json}`.
        - [ ] Determines execution order based on dependencies, conflicts, or predefined rules (e.g., dialogue before movement).
        - [ ] Returns an ordered list `[(char_id, action_details)]`.
    - [ ] Modify the loop to iterate through the *ordered actions*:
        - [ ] Call `apply_plan` for the action.
        - [ ] Update ground truth state.
        - [ ] Handle subjective outcome filtering and memory storage *after each action*.
    - [ ] Write/update unit tests focusing on the parallel request logic, the `resolve_and_sequence_plans` logic (various conflict scenarios), and the sequential execution loop. (Concurrency testing can be complex).

---

## Phase 10: Testing & Refinement (V1 Focus)

**Description:** Test V1 features, fix bugs, and refine prompts for the new architecture.
**Dependencies:** Phase 7, 8, 9.

### Subtask 10.1: V1 Unit & Integration Tests
- **Instructions:**
    - [ ] Review and ensure comprehensive unit test coverage for all new/modified V1 modules (`PerspectiveFilter`, `PlotManager`, `RelationshipManager`, `SimulationManager`, data models).
    - [ ] Expand integration tests:
        - [ ] Test `SimulationManager` running a multi-scene simulation with plot progression.
        - [ ] Verify subjective views are generated and passed correctly.
        - [ ] Verify relationship updates occur and influence subsequent actions (requires controlled LLM mocks or analysis).
        - [ ] Test parallel planning and action resolution logic.
        - [ ] Test plot guidance affects character selection and scene ending.

### Subtask 10.2: V1 Prompt Engineering & Refinement
- **Instructions:**
    - [ ] Run simulations focusing on V1 features.
    - [ ] Analyze LLM outputs specifically for:
        - [ ] Correct use of subjective context by characters.
        - [ ] Influence of relationships and goals on plans.
        - [ ] Adherence to plot beat objectives.
        - [ ] Quality of `PerspectiveFilter`'s subjective view generation (if LLM-based).
        - [ ] Quality of `PlotManager`'s scene ending judgment (if LLM-based).
    - [ ] Iteratively refine prompts for `CharacterAgent`, `PerspectiveFilter`, `PlotManager`, `RelationshipManager` based on V1 context.

### Subtask 10.3: Bug Fixing & Performance (V1)
- **Instructions:**
    - [ ] Address bugs specifically related to V1 features (subjectivity, plot, relationships, parallelism).
    - [ ] Profile runs, paying attention to potential bottlenecks in parallel planning or complex filtering/management logic.

---

## Phase 11: Advanced Memory - Vector Store Integration (V1 Context)

**Description:** Implement vector storage respecting V1's subjectivity and partitioning.
**Dependencies:** Phase 7 (Part 2 - Subjective Memory), Phase 10 (Stable V1 System).

### Subtask 11.1: Implement Vector Store Driver (as per Original Plan)
- **Instructions:**
    - [ ] Define `VectorStoreDriver` interface.
    - [ ] Implement `ChromaVectorStoreDriver` (or alternative).
        - [ ] Handle embedding generation.
        - [ ] Implement `add_memory`.
        - [ ] Implement `query_memories`.
    - [ ] Write unit tests for the driver.

### Subtask 11.2: Update MemoryManager for V1 Vector Store Use
- **Instructions:**
    - [ ] Modify `MemoryManager.__init__` for driver injection.
    - [ ] Update `MemoryManager.remember`:
        - [ ] Ensure it passes the `character_id` and `subjective_event` to `driver.add_memory`.
        - [ ] Store `character_id` in metadata for filtering.
    - [ ] Update `MemoryManager.retrieve`:
        - [ ] Generate query embedding.
        - [ ] Call `driver.query_memories`, ensuring the query is filtered by `character_id` using metadata.
        - [ ] Implement re-ranking considering mood, goals, relationship context (this logic likely stays in `MemoryManager` after getting candidates from the driver).
    - [ ] Update `MemoryManager.summarise_scene` to use LLM and store summary in vector store (associated with relevant characters or globally?).
    - [ ] Write/update unit tests for `MemoryManager` focusing on driver interaction, character_id filtering, and enhanced re-ranking.

---

## Phase 12: V1 Stretch Goals

**Description:** Implement advanced V1-aware features.
**Dependencies:** Phases 7-11.

### Subtask 12.1: V1-Aware UI Server (`server.py`)
- **Instructions:**
    - [ ] Set up FastAPI/Gradio.
    - [ ] Create endpoints/UI elements to:
        - [ ] Visualize plot structure (Acts/Beats) and current progress.
        - [ ] Display character states, including current subjective view highlights.
        - [ ] Show current relationship states between characters.
        - [ ] Allow inspection/modification of `PlotManager` state (e.g., force beat advance).
        - [ ] Start/stop/monitor simulations.

### Subtask 12.2: V1 Critic/Editor Agent
- **Instructions:**
    - [ ] Design critic prompts aware of plot structure, character goals, and relationship arcs.
    - [ ] Implement critic to evaluate narrative consistency against the V1 framework (e.g., "Did this scene advance the current beat's goals?").

### Subtask 12.3: V1 Tool-Calling
- **Instructions:**
    - [ ] Design tools relevant to the V1 context (e.g., tool to query `RelationshipManager` state, tool to check `PlotManager` beat status).
    - [ ] Implement tool use within `CharacterAgent` plan/reflect cycle, ensuring tools operate within the character's subjective context where appropriate.

---

This V1 plan prioritizes architectural changes earlier to minimize large refactors later. Original Phases 7, 8, 10, 11 are adapted and integrated into this new phased approach (New Phases 7-12).
