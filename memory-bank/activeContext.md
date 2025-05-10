# Active Context

Date: Fri May 10 00:20:00 PDT 2025 (Updated)

## Current Work Focus
- Completed Phase 1: Core project setup, data structures (`modules/models.py`), and configuration loading (`modules/config_loader.py`, `main.py`).
- Completed Phase 2: Basic `LLMInterface` (`modules/llm_interface.py`) and MVP `MemoryManager` (`modules/memory.py`), including comprehensive unit tests.
- Completed Phase 3: `CharacterAgent` implementation with its `reflect()` and `plan()` methods, including unit tests with proper prompt patterns.
- Completed Phase 4: `WorldAgent` core logic, heavily refactored to be LLM-driven for most narrative decisions, with configurable thresholds and comprehensive tests.
- **Completed Phase 5: `Narrator` module (`modules/narrator.py`) implementation, including prompt preparation, LLM interaction for prose generation, and unit tests. Introduced global configuration (`modules/ficworld_config.py`) for LLM model name, narrator tone, and tense.**

## What's Working
- Project directory structure and core files are in place.
- Core data models (`modules/models.py`) are defined.
- Configuration loading from presets, worlds, and roles (`modules/config_loader.py`) is functional.
- Initial `main.py` can parse arguments and load configurations.
- `LLMInterface` is set up to use OpenRouter, with comprehensive tests and a configurable default model name (`modules/ficworld_config.py`).
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
- Comprehensive unit tests for `WorldAgent` (`tests/test_world_agent.py`) are passing.
- **`Narrator` module (`modules/narrator.py`) is implemented and tested, using configurable default tone and tense from `modules/ficworld_config.py`. Uses synchronous LLM calls to prevent await issues.**

## What's Broken / To Be Implemented
- Full simulation loop in `main.py` (Phase 6).
- Advanced memory features (vector store integration, full Emotional RAG) are pending (Phase 7).
- Script mode functionality (Phase 8) - Basic hooks are in `WorldAgent` but need full implementation and testing in simulation loop.
- Comprehensive testing and debugging of the full loop (Phase 9).
- `TestCharacterAgent` has `RuntimeWarning: coroutine ... was never awaited` warnings that need to be addressed (likely by using an async test runner or adjusting test definitions). *(This was noted previously, should verify if still relevant after LLMInterface sync wrappers were added/used more widely).*

## Active Decisions and Considerations
- Proceeding with Phase 6: Full simulation loop in `main.py`.
- Ensuring the LLM-driven `WorldAgent` methods have robust fallback mechanisms when LLM calls fail or return unexpected results (current implementation has basic fallbacks).
- Prompt engineering for all LLM calls in `WorldAgent` and `Narrator` is crucial and will need ongoing refinement as the full simulation loop is tested.
- The interaction between `apply_plan` (generating textual outcome) and `update_from_outcome` (parsing text to update state) is a key area to monitor for consistency.
- **Consider making Narrator stylistic choices (tone, tense) configurable per Narrator instance or per run, beyond the global default, if finer control is needed.**

## Important Patterns and Preferences
- Adherence to design documents: `systemPatterns.md`, `prd.md`, `tasks.md`, `prompt_design.md`, `memory_strategy.md`.
- Modular design with clear separation of concerns for each component.
- Use of Python dataclasses for core data structures (`CharacterState` objects accessed via dot notation).
- Configuration-driven approach for simulations (now extended to `WorldAgent` thresholds and Narrator/LLM defaults via `modules/ficworld_config.py`).
- Comprehensive unit testing for each component.
- LLM-driven emergent behavior prioritized over hardcoded logic, especially in `WorldAgent` and `Narrator`.

## Learnings and Project Insights
- **Dataclass Attribute Access:** A significant debugging session was required to fix `AttributeError` and `TypeError` issues in `WorldAgent` and its tests. This was due to incorrectly trying to access `CharacterState` dataclass attributes using dictionary-style `get()` or `[]` instead of dot notation (e.g., `char_state.location`). This highlighted the importance of consistent object interaction patterns.
- **Testing Mutable State:** Debugging the `test_apply_plan_llm` failure revealed challenges in asserting state changes on mutable objects passed through several layers of method calls and mocks. Careful use of object ID checks and local variable assignments for assertion values helped isolate and confirm the fix.
- **LLM-Driven Design Benefits & Challenges:** Refactoring `WorldAgent` to be heavily LLM-driven increases flexibility and potential for emergence but also introduces complexity in prompt engineering, context management, and ensuring reliable parsing of LLM outputs (e.g., JSON from `update_from_outcome`). Fallback mechanisms become even more critical.
- **Configuration for Emergence:** Making thresholds (like max scene turns, event injection chances) in `WorldAgent` configurable allows for better control and tuning of the emergent narrative behavior. The addition of `ficworld_config.py` further enhances this for LLM and Narrator settings.
- **Async/Sync LLM Calls:** The `RuntimeWarning: coroutine ... was never awaited` in `test_narrator.py` highlighted the importance of correctly using synchronous wrappers (`generate_response_sync`) when calling async LLM interface methods from synchronous code. This ensures proper execution flow and testability.

## Current Database/Model State
- N/A (No persistent database is in use yet; memory is in-memory for MVP).
