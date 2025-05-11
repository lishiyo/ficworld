# Active Context

Date: Sat May 10 18:50:00 PDT 2025

## Current Work Focus
- **Completed Phase 6: Full simulation loop in `main.py` is now operational.**
- Previous phases (1-5) addressing core setup, data structures, LLM interface, memory manager, character agents, world agent, and narrator are also complete.

## What's Working
- **End-to-End Simulation:** The full simulation loop in `main.py` runs successfully, orchestrating all core components.
- **Component Functionality:**
    - `ConfigLoader` correctly loads presets, world definitions, and role archetypes.
    - `LLMInterface` successfully interacts with the configured LLM (OpenRouter).
    - `CharacterAgent`s perform their `reflect` (private thought, mood update) and `plan` (public action) cycles.
    - `WorldAgent` manages scene progression, turn order, applies character plans to generate factual outcomes, injects world events, and updates the `world_state` (including character states and environmental details) based on these outcomes.
    - `Narrator` renders the factual outcomes from each scene into narrative prose from a chosen character's point of view.
    - `MemoryManager` (MVP in-memory version) stores and retrieves memories for characters and performs basic scene summarization.
- **Output Generation:** The system generates `story.md` with the narrated prose and `simulation_log.jsonl` with detailed turn-by-turn events.

## What's Broken / To Be Implemented / Needs Improvement
- **Performance:** The most significant current issue is the slow execution speed of the simulation. This is primarily due to the high number of sequential LLM calls made within each scene (potentially 70-80 calls for a 10-turn scene).
- **Story Quality & Depth:** (General placeholder) While the loop works, ongoing refinement of prompts and logic will be needed to enhance narrative coherence, character depth, and overall story engagement.
- **Advanced Memory (Phase 7):** Vector store integration for LTM and full Emotional RAG implementation are pending.
- **Script Mode (Phase 8):** Full implementation and testing of `script_beats` functionality to guide the narrative are pending.
- **Comprehensive Testing (Phase 9):** While unit tests for individual modules are largely in place, more extensive integration testing of the full loop with diverse scenarios is needed.
- **Async Test Warnings:** Remaining `RuntimeWarning` and `DeprecationWarning` messages for `async` test methods in `test_character_agent.py` need to be addressed.

## Active Decisions and Considerations
- **Priority: Performance and Quality:** Before moving to more advanced features like Phase 7 (Advanced Memory) or fully implementing Phase 8 (Script Mode), the immediate focus should be on improving the performance of the current simulation loop and the quality of the generated narrative in "free" mode.
- **Strategies for Performance:** Investigate methods to reduce the number of LLM calls per scene, batch calls where possible (if applicable), or explore if any decision points can be handled heuristically or with less computationally intensive models without sacrificing too much quality.
- **Prompt Refinement:** Continuously iterate on prompts for all agents to improve the logical consistency and creativity of their outputs.

## Important Patterns and Preferences
- Adherence to design documents: `systemPatterns.md`, `prd.md`, `tasks.md`, `prompt_design.md`, `memory_strategy.md`.
- Modular design with clear separation of concerns.
- Use of Python dataclasses for core data structures.
- Configuration-driven approach for simulations, including LLM settings, world parameters, and agent behaviors.
- Comprehensive unit testing for each component, with a growing need for robust integration tests.
- Prioritization of LLM-driven emergent behavior, balanced with the need for performance and narrative coherence.

## Learnings and Project Insights
- **LLM Orchestration Complexity:** Successfully orchestrating a multi-agent system with numerous interdependent LLM calls for a full simulation loop is complex. Each agent's output influences the next, and managing state consistency while allowing for emergence is a key challenge.
- **Impact of Sequential LLM Calls:** The current architecture, with many sequential LLM calls per turn, directly impacts overall simulation speed. This highlights a common challenge in complex AI agent systems.
- **Value of Detailed Logging:** The `simulation_log.jsonl` is invaluable for debugging the intricate interactions and decision-making processes of the agents and the world.

## Current Database/Model State
- N/A (No persistent database is in use yet; memory is in-memory for MVP).
