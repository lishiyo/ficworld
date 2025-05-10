# Progress

Date: Fri May 10 00:20:00 PDT 2025

## Changes Since Last Update
- **World Agent Implementation (Phase 4 Completed):**
  - Implemented `WorldAgent` class in `modules/world_agent.py`.
  - Refactored core `WorldAgent` methods to be primarily LLM-driven for narrative decisions:
    - `judge_scene_end`: Uses LLM to evaluate scene conclusion based on narrative flow.
    - `choose_pov_character_for_scene`: Uses LLM to select the most compelling POV character.
    - `decide_next_actor`: Uses LLM to determine the next acting character based on dramatic potential.
    - `apply_plan`: Uses LLM to interpret character plans and generate rich textual outcomes.
    - `should_inject_event`: Uses LLM to decide if an environmental event is narratively appropriate.
    - `generate_event`: Can use LLM for contextual event generation, alongside script-triggered and random pool events.
    - `update_from_outcome`: Uses LLM to parse textual outcomes and extract structured state changes (location, conditions, time).
  - Made `WorldAgent` behavior configurable via `__init__` parameters for thresholds like max scene turns, event injection probabilities, and history limits.
  - Implemented robust fallback mechanisms for LLM-driven methods in case of API errors.
  - Corrected `CharacterState` attribute access from dictionary-style to dot notation throughout `WorldAgent`.
  - Updated `tests/test_world_agent.py` to reflect LLM-driven logic, configurable parameters, and fixed `CharacterState` access. All tests are passing.
  - Addressed an `AttributeError` in `generate_event` related to `current_beat` handling.

## Errors Encountered and Learnings
- **Dataclass Attribute Access:** Reinforced learning about correct attribute access (dot notation) for dataclass instances nested within other data structures, resolving multiple `AttributeError` and `TypeError` instances in `WorldAgent` and its tests.
- **Testing State Changes in Mutable Objects:** The `test_apply_plan_llm` failure highlighted the subtleties of testing modifications to mutable objects that are part of a larger state. Debugging involved careful tracing of object IDs and ensuring assertions accurately reflected the state at the precise moment of checking. Using local variables for assertion values proved helpful.
- **LLM-Driven Logic Trade-offs:** Transitioning `WorldAgent` to be heavily LLM-driven greatly enhances flexibility and emergent possibilities. However, it necessitates meticulous prompt engineering, robust error/fallback handling, and careful management of context provided to the LLMs. Parsing LLM outputs (especially for structured data like in `update_from_outcome`) also requires careful design.
- **Configuration for Fine-Tuning:** Making simulation parameters (e.g., scene length, event frequency) in `WorldAgent` configurable is crucial for allowing users or developers to fine-tune the narrative generation process without code changes.
- **Async Test Warnings:** Noted `RuntimeWarning` and `DeprecationWarning` for `async` test methods in `test_character_agent.py`. This will need to be addressed by potentially using an async-compatible test runner or framework adjustments for those specific tests.

## Next Steps Planned
- **Phase 5: Narrator Module Implementation:**
  - Define `Narrator` class in `modules/narrator.py`.
  - Implement the `render()` method to take a scene log and POV character information, and use an LLM with `NARRATOR_SYSTEM` and `NARRATOR_USER` prompts to generate narrative prose.
  - Write unit tests for the `Narrator` class.
- Address `async` test warnings in `test_character_agent.py`.

---
# Progress

Date: Fri May  9 22:38:17 PDT 2025

## Changes Since Last Update
- **Character Agent Implementation (Phase 3 Completed):**
  - Created `CharacterAgent` class in `modules/character_agent.py` with its core methods:
    - Implemented `__init__` method to store persona, goals, mood, and dependencies.
    - Implemented `reflect()` method for private introspection and mood updates based on world state and memories.
    - Implemented `plan()` method to generate structured JSON action plans influenced by mood and private reflection.
  - Implemented comprehensive unit tests in `tests/test_character_agent.py`, covering:
    - Initialization with correct field mappings from `RoleArchetype`
    - Proper construction of system prompts with relevant memory and world state context
    - Successful reflection with mood updates and internal thought generation
    - Structured plan generation with appropriate JSON validation
    - Error handling for edge cases in both reflection and planning
    - Synchronous wrapper functions for both main methods
  - Enhanced prompt engineering for both reflection and planning to align with `prompt_design.md` guidelines:
    - Updated prompts to include clearer context and instructions
    - Ensured proper JSON schema specification in the prompts
    - Added memory and world state information directly in system prompts

## Errors Encountered and Learnings
- **Data Model Field Name Consistency:** When implementing the `CharacterAgent` class, we found mismatches between the field names used in our tests and the actual field names in the `RoleArchetype` class. Tests were using `name`, `persona`, `goals`, and `starting_mood`, while the model defined `archetype_name`, `persona_template`, `goal_templates`, and `starting_mood_template`.
- **Learning:** It's important to ensure consistent field naming across the codebase and tests, especially when working with data models that are used in multiple places. When data models evolve, all dependent code and tests need to be updated to match.
- **Prompt Design Implementation:** Implementing the prompt guidelines from `prompt_design.md` required ensuring that memory and world state information is properly formatted and included in both system and user prompts.
- **Learning:** Dynamic prompt construction is more effective when the system prompt includes relevant context rather than relying solely on the user prompt. This allows the LLM to "stay in character" more consistently while also having access to memories and environment details.

## Next Steps Planned
- **Phase 4: World Agent Implementation:**
  - Define `WorldAgent` class in `modules/world_agent.py`
  - Implement scene management methods (`init_scene`, `judge_scene_end`, `choose_pov_character_for_scene`)
  - Implement actor and event management methods (`decide_next_actor`, `apply_plan`, `should_inject_event`, `generate_event`)
  - Write unit tests for `WorldAgent` class

Date: Fri May  9 22:11:12 PDT 2025

## Changes Since Last Update
- **Unit Tests for LLM Interface and Memory Manager (Phase 2 Completed):**
  - Implemented comprehensive unit tests for `LLMInterface` in `tests/test_llm_interface.py`, covering:
    - Successful initialization and API key handling
    - Text and JSON response generation (both async and sync methods)
    - Error handling for API errors and JSON parsing failures
    - Heuristic JSON parsing for responses
  - Implemented comprehensive unit tests for `MemoryManager` in `tests/test_memory.py`, covering:
    - Initialization and memory store management
    - Memory creation and storage (LTM and STM)
    - Memory retrieval (MVP implementation)
    - Scene summarization (MVP concatenation)
    - Memory clearing and resetting operations
  - Fixed a test issue in `test_summarise_scene_mvp` related to newline character representation in expected vs. actual output

## Errors Encountered and Learnings
- **Newline Character Representation in Tests:** When testing string equality with newline characters, we discovered that using escaped newlines (`\\n`) in the expected string created a mismatch with actual newlines (`\n`) in the output. This is because the escape sequence `\\n` in a string literal becomes a literal backslash followed by 'n' in the actual string, not a newline character.
- **Learning:** When writing tests involving multi-line strings, be careful with string literal representation, especially for special characters like newlines. Use raw strings (`r"..."`) or actual newline characters as appropriate for expected values.

## Next Steps Planned
- **Phase 3: Character Agent Implementation:**
  - Define `CharacterAgent` class in `modules/character_agent.py`
  - Implement the `__init__` method to store persona, goals, mood, and references to `LLMInterface` and `MemoryManager`
  - Implement the `reflect()` method to process world state and memories, update mood, and generate internal thoughts using the `CHARACTER_REFLECT` prompt
  - Implement the `plan()` method to generate a structured JSON action plan using the `CHARACTER_PLAN` prompt, influenced by mood and internal reflection
  - Create unit tests for the `CharacterAgent` class in `tests/test_character_agent.py`

---

Date: Fri May  9 21:29:44 PDT 2025

## Changes Since Last Update
- **Core Project Setup (Phase 1 Complete):**
    - Created `requirements.txt` with initial dependencies.
    - Created `README.md` with setup and usage instructions.
    - Defined core data structures (e.g., `MoodVector`, `RoleArchetype`, `WorldDefinition`, `Preset`, `MemoryEntry`, `LogEntry`) as Python dataclasses in `modules/models.py`.
    - Implemented `ConfigLoader` in `modules/config_loader.py` capable of loading presets, world definitions, and role archetypes from JSON files.
    - Created initial `main.py` with command-line argument parsing (for `--preset`) and logic to use `ConfigLoader` to load and display configurations.
    - Added `modules/__init__.py` to make `modules` a Python package.
    - Created sample data files:
        - World: `data/worlds/haunted_forest.json`
        - Roles: `data/roles/scholar.json`, `data/roles/knight.json`, `data/roles/mystic.json`
        - Preset: `presets/demo_forest_run.json`
    - Created sample prompt templates:
        - `data/prompts/character_reflect.txt`
        - `data/prompts/character_plan.txt`
- **LLM Interface & Basic Memory (Phase 2 Started):**
    - Implemented `LLMInterface` in `modules/llm_interface.py`, configured to use OpenRouter. This includes methods for generating text and JSON responses, with both async and sync versions.
    - Implemented an MVP `MemoryManager` in `modules/memory.py` with in-memory lists for short-term (STM) and long-term memory (LTM), and basic scene summarization (concatenation).
- **API Key Clarification:**
    - Updated `LLMInterface` and `README.md` (user performed direct edits) to use `OPENROUTER_API_KEY` as the environment variable for the API key, replacing the previous `OPENAI_API_KEY` for better clarity, although the `openai` Python library is still used for the API calls due to OpenRouter's compatibility.

## New Commands or Changes to Commands
- N/A in this update.

## Errors Encountered and Learnings
- **Initial API Key Confusion:** Initially, `OPENAI_API_KEY` was used for the OpenRouter service because its API is OpenAI-compatible. This was identified as potentially confusing.
- **Learning:** It's clearer to use an environment variable name that directly reflects the service being accessed (i.e., `OPENROUTER_API_KEY` for OpenRouter), even if the underlying client library is from a different provider (like `openai`). This improves maintainability and reduces ambiguity for new developers or users setting up the project.

## Next Steps Planned
- **Phase 3: Character Agent Implementation:**
    - Define `CharacterAgent` class in `modules/character_agent.py`.
    - Implement the `__init__` method to store persona, goals, mood, and references to `LLMInterface` and `MemoryManager`.
    - Implement the `reflect()` method to process world state and memories, update mood, and generate internal thoughts using the `CHARACTER_REFLECT` prompt.
    - Implement the `plan()` method to generate a structured JSON action plan using the `CHARACTER_PLAN` prompt, influenced by mood and internal reflection.

---
(Previous progress entries would be below this line if they existed)
