# Active Context

Date: Fri May  9 21:29:44 PDT 2025

## Current Work Focus
- Completed Phase 1: Core project setup, data structures (`modules/models.py`), and configuration loading (`modules/config_loader.py`, `main.py`).
- Completed initial parts of Phase 2: Basic `LLMInterface` (`modules/llm_interface.py`) and MVP `MemoryManager` (`modules/memory.py`).
- Addressed and corrected API key naming convention for OpenRouter (using `OPENROUTER_API_KEY` instead of `OPENAI_API_KEY`).
- Preparing to implement Phase 3: Character Agent core logic.

## What's Working
- Project directory structure and core files are in place.
- Core data models (`modules/models.py`) are defined.
- Configuration loading from presets, worlds, and roles (`modules/config_loader.py`) is functional.
- Initial `main.py` can parse arguments and load configurations.
- `LLMInterface` is set up to use OpenRouter (with the corrected API key variable `OPENROUTER_API_KEY`).
- Basic in-memory `MemoryManager` is implemented.
- Sample data files (world, roles, preset) and prompt templates created.

## What's Broken / To Be Implemented
- Full simulation loop in `main.py`.
- `CharacterAgent` class and its `reflect()` and `plan()` methods (Phase 3).
- `WorldAgent` class and its logic (Phase 4).
- `Narrator` module (Phase 5).
- Advanced memory features (vector store integration, full Emotional RAG) are pending (Phase 7).
- Script mode functionality (Phase 8).
- Comprehensive testing and debugging (Phase 9).

## Active Decisions and Considerations
- Proceeding with Phase 3: `CharacterAgent` implementation.
- Ensuring prompt templates in `data/prompts/` are correctly utilized by the agents.

## Important Patterns and Preferences
- Adherence to design documents: `systemPatterns.md`, `prd.md`, `tasks.md`, `prompt_design.md`, `memory_strategy.md`.
- Modular design with clear separation of concerns for each component.
- Use of Python dataclasses for core data structures.
- Configuration-driven approach for simulations.

## Learnings and Project Insights
- The importance of aligning environment variable names (`OPENROUTER_API_KEY`) with the actual service being used (OpenRouter) for clarity, even when using an OpenAI-compatible client library.
- Iterative creation of core files and sample data helps in verifying the config loading and data model definitions early on.

## Current Database/Model State
- N/A (No persistent database is in use yet; memory is in-memory for MVP).
