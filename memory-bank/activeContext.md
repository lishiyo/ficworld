# Active Context

Date: Fri May 10 00:15:00 PDT 2025

## Current Work Focus
- Completed Phase 1: Core project setup, data structures (`modules/models.py`), and configuration loading (`modules/config_loader.py`, `main.py`).
- Completed Phase 2: Basic `LLMInterface` (`modules/llm_interface.py`) and MVP `MemoryManager` (`modules/memory.py`), including comprehensive unit tests.
- Completed Phase 3: `CharacterAgent` implementation with its `reflect()` and `plan()` methods, including unit tests with proper prompt patterns.
- Completed Phase 4: `WorldAgent` core logic, heavily refactored to be LLM-driven for most narrative decisions, with configurable thresholds and comprehensive tests.

## What's Working
- Project directory structure and core files are in place.
- Core data models (`modules/models.py`) are defined.
- Configuration loading from presets, worlds, and roles (`modules/config_loader.py`) is functional.
- Initial `main.py` can parse arguments and load configurations.
- `LLMInterface` is set up to use OpenRouter, with comprehensive tests.
- Basic in-memory `MemoryManager` is implemented, with all tests passing.
- `CharacterAgent` with two-step thinking process (private `reflect()` and public `plan()`) is implemented, with prompts enhanced for creative action planning. All tests passing.
- `WorldAgent` (`modules/world_agent.py`) implemented with LLM-driven logic for:
    - Scene ending (`judge_scene_end`)
    - POV character selection (`choose_pov_character_for_scene`)
    - Next actor decision (`decide_next_actor`)
    - Plan application and outcome generation (`apply_plan`)
    - Event injection decisions (`should_inject_event`)
    - Event generation (`generate_event`)
    - World state updates from textual outcomes (`update_from_outcome`)
- `WorldAgent` includes configurable thresholds for scene length, event injection, etc.
- Comprehensive unit tests for `WorldAgent` (`tests/test_world_agent.py`) are passing after recent fixes.

## What's Broken / To Be Implemented
- `Narrator` module (Phase 5).
- Full simulation loop in `main.py` (Phase 6).
- Advanced memory features (vector store integration, full Emotional RAG) are pending (Phase 7).
- Script mode functionality (Phase 8) - Basic hooks are in `WorldAgent` but need full implementation and testing in simulation loop.
- Comprehensive testing and debugging of the full loop (Phase 9).
- `TestCharacterAgent` has `RuntimeWarning: coroutine ... was never awaited` warnings that need to be addressed (likely by using an async test runner or adjusting test definitions).

## Active Decisions and Considerations
- Proceeding with Phase 5: `Narrator` module implementation.
- Ensuring the LLM-driven `WorldAgent` methods have robust fallback mechanisms when LLM calls fail or return unexpected results (current implementation has basic fallbacks).
- Prompt engineering for all LLM calls in `WorldAgent` is crucial and will need ongoing refinement as the full simulation loop is tested.
- The interaction between `apply_plan` (generating textual outcome) and `update_from_outcome` (parsing text to update state) is a key area to monitor for consistency.

## Important Patterns and Preferences
- Adherence to design documents: `systemPatterns.md`, `prd.md`, `tasks.md`, `prompt_design.md`, `memory_strategy.md`.
- Modular design with clear separation of concerns for each component.
- Use of Python dataclasses for core data structures (`CharacterState` objects accessed via dot notation).
- Configuration-driven approach for simulations (now extended to `WorldAgent` thresholds).
- Comprehensive unit testing for each component.
- LLM-driven emergent behavior prioritized over hardcoded logic, especially in `WorldAgent`.

## Learnings and Project Insights
- **Dataclass Attribute Access:** A significant debugging session was required to fix `AttributeError` and `TypeError` issues in `WorldAgent` and its tests. This was due to incorrectly trying to access `CharacterState` dataclass attributes using dictionary-style `get()` or `[]` instead of dot notation (e.g., `char_state.location`). This highlighted the importance of consistent object interaction patterns.
- **Testing Mutable State:** Debugging the `test_apply_plan_llm` failure revealed challenges in asserting state changes on mutable objects passed through several layers of method calls and mocks. Careful use of object ID checks and local variable assignments for assertion values helped isolate and confirm the fix.
- **LLM-Driven Design Benefits & Challenges:** Refactoring `WorldAgent` to be heavily LLM-driven increases flexibility and potential for emergence but also introduces complexity in prompt engineering, context management, and ensuring reliable parsing of LLM outputs (e.g., JSON from `update_from_outcome`). Fallback mechanisms become even more critical.
- **Configuration for Emergence:** Making thresholds (like max scene turns, event injection chances) in `WorldAgent` configurable allows for better control and tuning of the emergent narrative behavior.

## Current Database/Model State
- N/A (No persistent database is in use yet; memory is in-memory for MVP).
