# V0 Improvements 

We are currently doing [story_loop](./story_loop.md). However, the story it generates is super clunky and doesn't reflect how real characters might behave.

Here are some initial thoughts I have on what can be improved:

1) each character role needs:
    - an actual name, not just `archetype_name`
    - a deep backstory, not just persona (the personality)

Highly Feasible. This primarily involves expanding the character data model (CharacterState) and updating the prompts used in reflect and plan to leverage this richer context.

2) for `get_world_state_view_for_actor` - we need the world state from THEIR perspective, this wouldn't be the same for everyone because everyone has a different perspective

Feasible but Complex. The current `story_loop.md` suggests a single objective world_state informs the current_world_view. Implementing subjective views requires adding a filtering layer (potentially LLM-based or rule-based) before passing the state to an actor, ensuring they only "see" what they should reasonably know. This ties closely into the memory improvement.

3) characters should only be remembering only what they actually witness or get told or should know from general world facts - i.e., each character should have DIFFERENT memory streams since there's a lot they don't know that others would

Feasible, likely requires refinement. `story_loop.md` implies individual memory storage (character_remembers, retrieve). The key challenge is ensuring the input `current_world_view` is also filtered based on individual knowledge, preventing omniscience even if memories are separate.

4) looking at [the simulation log](../outputs/demo_forest_run/simulation_log.jsonl), the current actions are always "speak" - we need to encourage many more kinds, including "do nothing"

Highly Feasible. This is largely a prompt engineering challenge for the plan_sync LLM call. We need to explicitly encourage a wider range of actions (including physical actions, non-actions, environmental interactions) and ensure apply_plan can handle them.

5) characters actions shouldn't be sequential - it's not one character acting one at a time, it's multiple at once in a scene
  - perhaps some of these should be parallel calls, while others are more sequential

Very Complex. This is a fundamental shift from the current turn-based sequential model described in story_loop.md. It would require rethinking the core turn loop, how multiple simultaneous plans are generated, and how conflicting actions are resolved by the WorldAgent. This introduces significant architectural complexity. **A potential middle ground could be allowing multiple characters to plan simultaneously based on the same state, then having the WorldAgent resolve and execute these plans sequentially or in a determined order within the turn.**

5) it shouldn't be a random selection of characters each scene, in reality characters will cluster around their subplots and narrative threads - for example you could have an initial main character who just has her friends and family, then she ends up with a superhero team, they clash with the villain team, then we learn more about one of the villains' backstory and so on
    - we need to order a story in not just scenes, but "narrative threads" (e.g. A plot vs B plot) where characters are tied to certain threads that weave into each other and finally culminate together

Feasible but Complex. This requires introducing a higher-level concept of plot structure (e.g., NarrativeThread) beyond individual scenes. The WorldAgent's logic for initializing scenes (init_scene) and selecting actors (decide_next_actor) would need to become aware of these threads to guide character participation and interaction, likely needing a dedicated "Plot Manager" component or significantly enhanced WorldAgent logic.

6) in the "free" style (no script), we should strive to follow a high-level narrative structure like in Blake Snyder's Save the Cat Beat Sheet:
    - Act 1 (Thesis):
        - set-up, the status quo
        - new situation and change of plans, inciting incident, the catalyst
    - Act 2 (Antithesis):
        - rising action, adapt and search, encounter first obstacle
        - meet tests, allies, enemies
        - fun and games to the Midpoint
        - at the Midpoint, the bad guys close in, false victory/defeat, we get complications, higher stakes, major setback
        - end with dark night of the soul
    - Act 3 (Synthesis):
        - climactic choice - towards strength, or worsens flaw
        - possible twist, new tension
        - resolution

Feasible but Complex. Similar to Narrative Threads, this requires adding a meta-layer to track the story's progression through structural beats (Setup, Inciting Incident, Rising Action, Midpoint, etc.). Prompts for various agents (WorldAgent, CharacterAgent) would need conditioning based on the current beat's narrative goals, especially in "free" mode.

7) Once we get "beats" in, we should make a script to take in an example good story and parse it into all the initial config - roles, worlds, preset, beats and so on, this will help us test it out
    - we can start with a short story first, then try a full story like a Pixar movie

Feasible (Offline Tool). This is a separate utility script. It would use LLMs to parse existing stories and generate the necessary JSON/data files for roles, world, beats, etc., streamlining the setup process for testing.

8) For the Narrator agent, we should finetune based on an author's style that we like (perhaps we can finetune on different favorite authors in different genres, then allow users to select a style)
    - for a first pass, we can try to adjust this in the prompt (e.g. "Write like Kazuo Ishiguro", "Write like George RR Martin") where the user can input the author's name

Simple prompting ("Write like...") is easy to implement immediately within the Narrator.render call. Fine-tuning offers better results but requires data and setup.

Additional Suggestions for Improvement:

1. Explicit Relationship Model: Track dynamic relationships between characters (e.g., friend, enemy, trust level, romantic interest). This adds depth and realism, influencing how characters reflect, plan, and how the WorldAgent might pair them or interpret interactions.

2. Stronger Goal-Driven Planning: Enhance the plan prompt to heavily weigh the character's explicit short-term and long-term goals. This encourages more proactive and less purely reactive behavior.

3. Environmental Interaction: Explicitly encourage characters to interact with their surroundings (environment_description, specific objects) in the plan prompt, not just converse. `apply_plan` would need to process these actions.

4. Smarter Scene Pacing/Endings: Refine the judge_scene_end logic. Instead of just checking if the scene feels "done," consider narrative goals. Should it end on a cliffhanger? Resolve a minor point? Introduce something new based on the current plot beat?

I think this should be dependent on where we are at the higher-level narrative structure, (i.e. the Save the Cat Beat Sheet)

5. Leverage Scene Summaries: Use the output of MemoryManager.summarise_scene as input for characters in subsequent scenes (perhaps during reflect or plan) to improve long-term memory and continuity.

6. Optimize LLM Calls: The current loop (~70-80 LLM calls per scene example in story_loop.md) is very high. Consider:
    - **Combining reflect and plan into one call**
    - Using non-LLM methods (regex, simple logic) for deterministic state updates in update_from_outcome where possible.
    - Using heuristics or weighted randomness for decide_next_actor or should_inject_event sometimes, instead of always relying on an LLM.

---

## What We Want To Do

### A. Highly feasible

1) Refine each character role to include:
    - an actual name, not just `archetype_name`
    - a deep backstory, not just persona (the personality)

This primarily involves expanding the character data model (`CharacterState`) and updating the prompts used in reflect and plan to leverage this richer context.

2) Looking at [the simulation log](../outputs/demo_forest_run/simulation_log.jsonl), the current actions are always "speak" - we need to encourage many more kinds, including "do nothing"

This is largely a prompt engineering challenge for the `plan_sync` LLM call. We need to explicitly encourage a wider range of actions (including physical actions, non-actions, environmental interactions) and ensure apply_plan can handle them.

3) For the Narrator agent, we should allow user to set an author voice (e.g. "write like George RR Martin"). For now we can set it via a `.env` config like `AUTHOR_STYLE`.

Simple prompting ("Write like...") is easy to implement immediately within the Narrator.render call.

4) Stronger Goal-Driven Planning: Enhance the plan prompt to heavily weigh the character's explicit short-term and long-term goals. This encourages more proactive and less purely reactive behavior.

This is primarily a prompt engineering task, assuming character goals are already part of their data model. It involves adjusting the LLM prompts for `plan_sync` to give more weight to these goals.

5) Environmental Interaction: Explicitly encourage characters to interact with their surroundings (environment_description, specific objects) in the plan prompt, not just converse. apply_plan would need to process these actions.

This is also largely a prompt engineering task for `plan_sync`. `apply_plan` would need to be robust enough to handle a wider variety of action types, but the core change is in encouraging the LLM to generate these actions.

### B. Feasible

1) Leverage Scene Summaries: Use the output of `MemoryManager.summarise_scene` as input for characters in subsequent scenes (perhaps during `reflect` or `plan`) to improve long-term memory and continuity.

This requires piping the existing scene summaries into the context for characters in later scenes. It's mainly a data flow adjustment and updating the relevant prompts.

2) Explicit Relationship Model: Track dynamic relationships between characters (e.g., friend, enemy, trust level, romantic interest). This adds depth and realism, influencing how characters reflect, plan, and how the WorldAgent might pair them or interpret interactions.

This involves some data model changes (to store relationship states) and updates to prompts for reflect and plan to utilize this information. It's comparable to adding detailed backstories.

### C. Feasible but complex

1) Improve `current_world_view` to include subjective views:
    - for `get_world_state_view_for_actor` - we need the world state from THEIR perspective, this wouldn't be the same for everyone because everyone has a different perspective
        - The current `story_loop.md` suggests a single objective `world_state` informs the `current_world_view`. Implementing subjective views requires adding a filtering layer (potentially LLM-based or rule-based) before passing the state to an actor, ensuring they only "see" what they should reasonably know.
    - characters should only be remembering what they actually witness or get told or should know from general world facts - i.e., each character should have DIFFERENT memory streams since there's a lot they don't know that others would
        - The key challenge is ensuring the input `current_world_view` is *also* filtered based on individual knowledge, preventing omniscience even if memories are separate.

2) Make multiple characters act at once in a scene, instead of sequentially - we'll do the middle ground of allowing multiple characters to plan simultaneously based on the same state, then having the `WorldAgent` resolve and execute these plans sequentially or in a determined order within the turn.

### D. Tasks AFTER we do Beats

1) After we get "beats" in, we should make a script to take in an example good story and parse it into all the initial config - roles, worlds, preset, beats and so on, this will help us test it out
    - we can start with a short story first, then try a full story like a Pixar movie

This is a separate utility script. It would use LLMs to parse existing stories and generate the necessary JSON/data files for roles, world, beats, etc., streamlining the setup process for testing.

2) In Free mode, introduce narrative threads grouping characters + use the "Save the Cat" beats overarching structure

We'll introduce a higher-level concept of plot structure (e.g., `NarrativeThread`) beyond individual scenes. The WorldAgent's logic for initializing scenes (`init_scene`) and selecting actors (`decide_next_actor`) would need to become aware of these threads to guide character participation and interaction. We'll use a dedicated "Plot Manager" component.

Similar to Narrative Threads, an overarching structure requires adding a meta-layer to track the story's progression through structural beats (Setup, Inciting Incident, Rising Action, Midpoint, etc.). Prompts for various agents (WorldAgent, CharacterAgent) would need conditioning based on the current beat's narrative goals, especially in "free" mode.

We should combine these two in a Plot Manager that tracks the overall structural beats and tracks the characters that are involved in each thread (e.g. the villains are their own NarrativeThread and enter during Act I).

3) Smarter Scene Pacing/Endings: Refine the `judge_scene_end` logic. Instead of just checking if the scene feels "done," consider narrative goals. Should it end on a cliffhanger? Resolve a minor point? Introduce something new based on the current plot beat?

Thi is tied to the broader narrative structure we introduced above. If the system has awareness of something like the Save the Cat beats, then `judge_scene_end` can make more informed decisions. This makes it reliant on implementing that higher-level structure first or concurrently.

---

## Target Architecture Plan (incorporating all improvements)

This outlines a potential architecture evolving from the `story_loop.md` baseline to support all the desired features (A, B, C, D). It's designed for incremental implementation.

**I. Core Components:**

1.  **`SimulationManager` (Evolved `main.py` loop):**
    *   Orchestrates the overall simulation flow (scenes, acts).
    *   Loads configuration (preset, world, roles, plot structure).
    *   Initializes and manages other core components (`WorldAgent`, `PlotManager`, `MemoryManager`, `Narrator`, `CharacterAgents`).
    *   Handles top-level progression based on `PlotManager` guidance.

2.  **`WorldAgent`:**
    *   Manages the "ground truth" `world_state` (objective reality).
    *   Manages the **Turn Loop** within a scene.
        *   Receives guidance from `PlotManager` on scene goals/relevant actors.
        *   *Handles parallel planning:* Requests plans from multiple selected characters simultaneously based on the *same* state snapshot.
        *   *Resolves/sequences plans:* Determines the order of execution for potentially conflicting/simultaneous plans.
        *   *Executes actions sequentially:* Calls `apply_plan` for each resolved action, updating the ground truth `world_state` after *each individual action*.
    *   `apply_plan`: Processes a single character's action, determines the objective `factual_outcome` (potentially using fewer LLMs for simple actions like movement), and updates the ground truth `world_state`.
    *   Interacts with `RelationshipManager` to update character relationships based on outcomes.
    *   Handles injection of world events (potentially guided by `PlotManager`).
    *   Selects POV character for narration (potentially guided by `PlotManager`).

3.  **`CharacterAgent` (Pool managed by `SimulationManager`):**
    *   Represents an individual character.
    *   Holds character-specific static data (`full_name`, `backstory`, `persona`, `initial_goals`).
    *   Receives a `subjective_world_view` from the `PerspectiveFilter`.
    *   Receives context: `relevant_memories`, `relationship_summary`, `active_goals`, `current_plot_context`.
    *   Performs `reflect` and `plan` (potentially combined/modified for efficiency).
        *   Prompts enhanced for: backstory, goals, relationships, environmental interaction, varied actions, author style (indirectly via persona?).
        *   Outputs a proposed `plan_json`.
    *   Interacts with its assigned `MemoryManager` instance/partition.

4.  **`MemoryManager`:**
    *   Manages memory persistence (e.g., vector DB).
    *   Partitioned or filtered by character.
    *   `remember(character_id, subjective_event_details, world_state_context)`: Stores memories *only* based on what the character could perceive (filtered input).
    *   `retrieve(character_id, query)`: Retrieves memories relevant to the character.
    *   `summarise_scene(scene_log)`: Creates a scene summary (as currently).
    *   Provides access to scene summaries as long-term context for characters.

5.  **`Narrator`:**
    *   Receives scene log, POV character info, and author style (`AUTHOR_STYLE` from config).
    *   Renders the scene into prose using LLM.

6.  **`PerspectiveFilter` (New Component):**
    *   Sits between `WorldAgent` (ground truth) and `CharacterAgents`.
    *   `get_view_for(character_id, ground_truth_world_state, character_memory_access)`:
        *   Filters the objective `world_state` based on the character's location, senses, prior knowledge (from memory access), and potentially relationship-based information sharing.
        *   Can start rule-based (e.g., visibility cones) and become LLM-enhanced for social inference.
        *   Returns the `subjective_world_view` for that character.

7.  **`PlotManager` (New Component):**
    *   Manages the high-level narrative structure (e.g., Acts, Beats based on Save the Cat).
    *   Tracks the current Act and Beat.
    *   Manages `NarrativeThreads` (e.g., A-plot, B-plot) and associated characters.
    *   Provides guidance to `WorldAgent`:
        *   Suggests relevant characters/settings for `init_scene` based on current beat/threads.
        *   Helps `decide_next_actor` by prioritizing characters relevant to active threads/beat goals.
        *   Informs `judge_scene_end` logic based on whether beat objectives are met.
        *   Can trigger plot-relevant world events via `WorldAgent`.

8.  **`RelationshipManager` (New Component or `WorldAgent` Sub-module):**
    *   Tracks dynamic relationship states between characters (e.g., friend, enemy, rival, romantic interest, trust levels).
    *   Provides relationship context to `CharacterAgent` prompts via `PerspectiveFilter` or directly.
    *   Updated by `WorldAgent` based on interaction outcomes.

**II. Data Model Enhancements:**

*   **`CharacterState` (within `WorldAgent`'s ground truth):** Objective state like `location`, `physical_condition`, `inventory`.
*   **`CharacterConfig` (Loaded at start):** `full_name`, `persona`, `backstory`, `initial_goals` (long-term, short-term).
*   **`WorldState` (Ground Truth):** Time, environment, character states, object states, recent objective events log.
*   **`SubjectiveWorldView` (Generated by `PerspectiveFilter`):** Filtered version of `WorldState` specific to a character.
*   **`RelationshipState`:** Stored by `RelationshipManager`, e.g., `{(char_a, char_b): {'trust': 0.8, 'affinity': 0.5, 'status': 'allies'}}`.
*   **`PlotStructure`:** Defines Acts and Beats (`id`, `name`, `description`, `narrative_goals`).
*   **`NarrativeThread`:** `id`, `name`, `character_ids`, `status`, `summary`, `associated_beats`.
*   **`Plan`:** JSON output from `CharacterAgent`.
*   **`FactualOutcome`:** Objective text description of what happened after `apply_plan`.

**III. Key Interaction Flow Changes (Example Turn with Parallel Planning):**

1.  `SimulationManager` advances scene/turn.
2.  `PlotManager` provides context (current beat goals, relevant threads/characters) to `WorldAgent`.
3.  `WorldAgent` identifies active characters (e.g., `[Alice, Bob]`) for this turn based on state and `PlotManager` guidance.
4.  `WorldAgent` gets current ground truth `world_state`.
5.  **Parallel Execution:**
    *   `WorldAgent` requests `subjective_world_view` for Alice from `PerspectiveFilter(world_state)`.
    *   `WorldAgent` requests `subjective_world_view` for Bob from `PerspectiveFilter(world_state)`.
    *   `WorldAgent` requests `plan` from `Alice_Agent` using `Alice_subjective_view`, memories, goals, relationships.
    *   `WorldAgent` requests `plan` from `Bob_Agent` using `Bob_subjective_view`, memories, goals, relationships.
6.  `WorldAgent` receives `plan_Alice` and `plan_Bob`.
7.  `WorldAgent` resolves/sequences plans (e.g., Alice speaks first, then Bob moves). Let's say resolved order is `[action_Alice, action_Bob]`.
8.  `WorldAgent` executes `action_Alice` via `apply_plan(Alice, action_Alice)`.
    *   Gets `outcome_Alice`.
    *   Updates ground truth `world_state`.
    *   Updates `RelationshipManager` if needed.
    *   `PerspectiveFilter` determines who observed `outcome_Alice`. Sends filtered outcome to relevant `MemoryManager` partitions (e.g., Alice remembers, Bob remembers if he saw/heard it).
9.  `WorldAgent` executes `action_Bob` via `apply_plan(Bob, action_Bob)`.
    *   Gets `outcome_Bob`.
    *   Updates ground truth `world_state`.
    *   Updates `RelationshipManager`.
    *   `PerspectiveFilter` determines observers. Sends filtered outcome to `MemoryManager`.
10. Turn ends (or proceeds to world event check, etc.). Characters might `reflect` here based on the turn's final state or after their own action.

**IV. Implementation Phasing:**

*   **Phase 1 (Highly Feasible):** Focus on `CharacterConfig` enrichment, prompt updates (actions, goals, environment), `Narrator` style config. Minimal structural change.
*   **Phase 2 (Feasible):** Add `RelationshipManager`, integrate scene summaries. Requires data model changes and prompt updates.
*   **Phase 3 (Complex - Subjectivity & Memory):** Implement `PerspectiveFilter`, modify `WorldAgent` to use ground truth, update `CharacterAgent` to use subjective views, refine `MemoryManager` input filtering. Major data flow change.
*   **Phase 4 (Complex - Parallel Planning):** Modify `WorldAgent` turn loop for parallel plan requests and resolution. Significant logic change in `WorldAgent`.
*   **Phase 5 (Complex - Plot):** Introduce `PlotManager`, Beats, Threads. Integrate with `WorldAgent` guidance and `judge_scene_end`. Build offline story parser tool. Requires new components and integration.

