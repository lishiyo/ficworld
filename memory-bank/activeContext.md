# Active Context

Date: Fri May  9 22:38:17 PDT 2025

## Current Work Focus
- Completed Phase 1: Core project setup, data structures (`modules/models.py`), and configuration loading (`modules/config_loader.py`, `main.py`).
- Completed Phase 2: Basic `LLMInterface` (`modules/llm_interface.py`) and MVP `MemoryManager` (`modules/memory.py`), including comprehensive unit tests.
- Completed Phase 3: `CharacterAgent` implementation with its `reflect()` and `plan()` methods, including unit tests with proper prompt patterns.
- Preparing to implement Phase 4: World Agent core logic.

## What's Working
- Project directory structure and core files are in place.
- Core data models (`modules/models.py`) are defined.
- Configuration loading from presets, worlds, and roles (`modules/config_loader.py`) is functional.
- Initial `main.py` can parse arguments and load configurations.
- `LLMInterface` is set up to use OpenRouter (with API key variable `OPENROUTER_API_KEY`), with comprehensive tests.
- Basic in-memory `MemoryManager` is implemented, with all tests passing.
- `CharacterAgent` with two-step thinking process (private `reflect()` and public `plan()`) is implemented, with all tests passing.
- Prompt engineering based on guidelines in `prompt_design.md` has been applied to the `CharacterAgent` class.

## What's Broken / To Be Implemented
- `WorldAgent` class and its logic (Phase 4).
- `Narrator` module (Phase 5).
- Full simulation loop in `main.py` (Phase 6).
- Advanced memory features (vector store integration, full Emotional RAG) are pending (Phase 7).
- Script mode functionality (Phase 8).
- Comprehensive testing and debugging (Phase 9).

## Active Decisions and Considerations
- Proceeding with Phase 4: `WorldAgent` implementation.
- Making sure prompt templates in the character agent align with the guidelines in `prompt_design.md`.
- Ensuring proper field mappings between data models and classes that use them.

## Important Patterns and Preferences
- Adherence to design documents: `systemPatterns.md`, `prd.md`, `tasks.md`, `prompt_design.md`, `memory_strategy.md`.
- Modular design with clear separation of concerns for each component.
- Use of Python dataclasses for core data structures.
- Configuration-driven approach for simulations.
- Comprehensive unit testing for each component.
- Two-step thinking process for character agents (private reflection then public planning).

## Learnings and Project Insights
- The importance of aligning environment variable names (`OPENROUTER_API_KEY`) with the actual service being used (OpenRouter) for clarity, even when using an OpenAI-compatible client library.
- When writing tests involving multi-line strings, be careful with string literal representation, especially for special characters like newlines.
- Field names in data models (like `RoleArchetype`) need to be consistently referenced throughout the codebase, and tests need to be updated when data models evolve.
- The `CharacterAgent` needs to dynamically format memory and world state for the system prompt to ensure contextually relevant responses.

## Current Database/Model State
- N/A (No persistent database is in use yet; memory is in-memory for MVP).
