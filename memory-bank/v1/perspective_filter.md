# Perspective Filter: Crafting Subjective Realities in FicWorld

## 1. Introduction: The Importance of Subjective Perception

In FicWorld, the goal is to create a dynamic and believable narrative driven by character interactions and their understanding of the world. A key aspect of this is recognizing that not all characters perceive events or their surroundings identically. Each character has their own biases, emotional state, goals, and physical limitations that color their interpretation of reality.

The `PerspectiveFilter` module is central to achieving this. It acts as a bridge between the objective, "ground truth" state of the world and the individual, subjective experiences of each character. This allows for:

*   **Realistic Information Asymmetry:** Characters only know what they see, hear, or infer.
*   **Varied Interpretations:** The same event can be perceived differently by different characters, leading to misunderstandings or unique insights.
*   **Deeper Characterization:** A character's internal state (mood, goals) directly influences how they interpret their environment and the actions of others.
*   **Emergent Narrative:** Subjectivity can lead to unexpected plot developments as characters act on their (potentially flawed) understanding of the world.

## 2. Objective Reality: The Ground Truth Managed by `WorldAgent`

Before a character can have a subjective view, there must be an objective reality to perceive. This ground truth is managed by the `WorldAgent` and primarily encapsulated within the `WorldState` object. Key components of this objective reality include:

### 2.1. `WorldState` (from `modules.models.py`)

This dataclass serves as the comprehensive snapshot of the entire game world from an omniscient viewpoint at a specific moment. It contains, among other things:
*   Global event logs.
*   Current narrative time.
*   A dictionary of `CharacterState` objects.
*   A dictionary of `LocationState` objects.
*   A dictionary of `ObjectState` objects.

### 2.2. `LocationState` (Pydantic model in `modules.data_models.py`)

*   **Purpose**: To objectively describe a specific location in the game world.
*   **Key Attributes**:
    *   `id: str`: Unique identifier (e.g., "forest_clearing_01").
    *   `name: str`: Common name (e.g., "Sunken Glade").
    *   `description: str`: An objective, factual description of the location (e.g., "A low-lying glade often damp, with large, moss-covered stones.").
    *   `objects_present: List[str]`: A list of `id`s for all `ObjectState` instances factually currently in this location.
    *   `characters_present: List[str]`: A list of `id`s for all `CharacterState` instances factually currently in this location.
*   **Example**:
    ```json
    {
      "id": "loc_grimoire_library",
      "name": "The Forbidden Library",
      "description": "Ancient stone shelves line the walls, filled with decaying tomes. A faint smell of ozone hangs in the air.",
      "objects_present": ["obj_lectern_01", "obj_grimoire_01"],
      "characters_present": ["char_elara", "char_silas"]
    }
    ```

### 2.3. `ObjectState` (Pydantic model in `modules.data_models.py`)

*   **Purpose**: To objectively describe a specific object in the game world.
*   **Key Attributes**:
    *   `id: str`: Unique identifier (e.g., "obj_ancient_sword_01").
    *   `name: str`: Common name (e.g., "Blade of Whispers").
    *   `description: str`: An objective, factual description of the object (e.g., "A longsword with a dark, intricately carved hilt. It seems to absorb light.").
    *   `state: str`: The current objective condition or status of the object (e.g., "sheathed", "on_pedestal", "broken", "glowing_faintly").
    *   `is_interactive: bool`: A flag indicating if the object can generally be interacted with.
*   **Example**:
    ```json
    {
      "id": "obj_grimoire_01",
      "name": "The Umbral Grimoire",
      "description": "A heavy, leather-bound book with a clasp in the shape of a coiled serpent. Its pages are brittle.",
      "state": "closed_on_lectern",
      "is_interactive": true
    }
    ```

### 2.4. `CharacterState` (Dataclass in `modules.models.py`)

*   **Purpose**: While `CharacterConfig` (from `modules.data_models.py`) defines the static template of a character, `CharacterState` (managed within `WorldState`) holds their *current objective properties*.
*   **Key Attributes (Objective ones relevant to perception)**:
    *   `name: str`: Character's name.
    *   `location: str`: The `id` of the `LocationState` where the character is objectively present.
    *   `current_mood: MoodVector`: The character's actual internal emotional state.
    *   `goals: List[str]`: The character's current active goals.
    *   `persona: str`: The character's core personality description.
    *   (Other attributes like inventory, conditions etc.)

## 3. The `PerspectiveFilter` Module: Bridging Objective and Subjective

The `PerspectiveFilter` is responsible for taking the objective `WorldState` and, for a given character, generating their unique `SubjectiveWorldView` and interpreting events into `SubjectiveEvent`s. It primarily uses an LLM to achieve this, providing the LLM with carefully constructed prompts containing both objective facts and character-specific context.

*   **Initialization**: `PerspectiveFilter(llm_interface: LLMInterface, memory_manager: MemoryManager)`
    *   It requires an `LLMInterface` to make calls to the language model.
    *   It requires a `MemoryManager` to fetch a character's relevant memories, which can influence their current perception.

### 3.1. Core Method: `get_view_for(character_id: str, ground_truth_world_state: WorldState) -> SubjectiveWorldView`

This is the primary method for generating what a character "sees" and "understands" about their current environment.

*   **Inputs**:
    *   `character_id: str`: The ID of the character whose perspective is being generated.
    *   `ground_truth_world_state: WorldState`: The current objective state of the world.
*   **Process**:
    1.  **Gather Character Context**:
        *   Retrieve the character's `CharacterState` from `ground_truth_world_state`. This provides their objective location, current mood, goals, persona, etc.
        *   Fetch relevant memories for this character from the `MemoryManager` (e.g., using `memory_manager.retrieve(character_id)`). These memories (past `SubjectiveEvent`s or `MemoryEntry` objects) provide personal history that can affect interpretation.
        *   (Future) Fetch relationship summaries with other characters present (e.g., from a `RelationshipManager`).
    2.  **Prepare LLM Prompt**: Construct a detailed prompt for the LLM. This prompt includes:
        *   The observing character's full profile (name, persona, backstory, current mood, active goals).
        *   Their relevant memories.
        *   Their relationship summaries (if available).
        *   The *objective* details from `ground_truth_world_state`:
            *   The character's current `LocationState` (description, other characters present, objects present).
            *   The `ObjectState` for all objects in that location.
            *   The `CharacterState` for all other characters in that location (name, general description, current mood if perceivable).
            *   Relevant recent global events or environmental details.
        *   Clear instructions for the LLM to interpret this information from the character's specific point of view, considering their physical senses, knowledge, biases, emotional state, and goals.
        *   Instructions to format the output as a JSON object strictly adhering to the `SubjectiveWorldView` Pydantic model.
    3.  **LLM Call**: Send the prompt to the LLM via `llm_interface.call_llm()`.
    4.  **Parse Response**: Parse the LLM's JSON response into a `SubjectiveWorldView` object. Implement robust error handling for malformed JSON or API errors.
*   **Output**: A `SubjectiveWorldView` Pydantic model object. This model (defined in `modules.data_models.py`) includes:
    *   `character_id: str`: The observer.
    *   `timestamp: str`: When this view was generated.
    *   `perceived_location_id: str`: The ID of the location.
    *   `perceived_location_description: str`: The character's *subjective description* of the location.
    *   `visible_characters: List[VisibleCharacterState]`: A list of characters the observer perceives, including their `estimated_condition`, `apparent_mood`, and `observed_action` *from the observer's POV*.
    *   `visible_objects: List[VisibleObjectState]`: A list of objects the observer perceives, including their `observed_state` and `perceived_usability` *from the observer's POV*.
    *   `recent_perceived_events: List[SubjectiveEvent]`: A list of recent events *as the character perceived them*.
    *   `inferred_context: str`: The character's overall understanding or inference about the current situation.
    *   `active_focus_or_goal: Optional[str]`: What the character might be immediately focusing on or a micro-goal derived from their perception.

### 3.2. Event Perception Method: `get_subjective_event(observer_id: str, factual_outcome: str, ground_truth_world_state: WorldState, actor_id: Optional[str] = None, target_id: Optional[str] = None) -> SubjectiveEvent`

This method is called after an objective event (a `factual_outcome` from `WorldAgent.apply_plan`) has occurred to determine how a specific observer perceived it.

*   **Inputs**:
    *   `observer_id: str`: The ID of the character perceiving the event.
    *   `factual_outcome: str`: The objective description of what happened.
    *   `ground_truth_world_state: WorldState`: The world state *after* the event.
    *   `actor_id: Optional[str]`: The ID of the character who primarily caused the event (if any).
    *   `target_id: Optional[str]`: The ID of the character or object primarily affected by the event (if any).
*   **Process**:
    1.  **Gather Observer Context**: Similar to `get_view_for`, retrieve the observer's `CharacterState`, relevant memories, and relationship context (especially with the `actor_id` and `target_id`).
    2.  **Prepare LLM Prompt**: Construct a prompt that includes:
        *   The observer's profile and relevant context.
        *   The `factual_outcome`.
        *   Details about the `actor_id` and `target_id` (if provided) from `ground_truth_world_state`.
        *   Instructions for the LLM to re-interpret the `factual_outcome` from the observer's unique perspective, considering their senses, biases, emotional state, and relationship to those involved. The LLM should generate the fields for the `SubjectiveEvent` model.
        *   Instructions to format the output as a JSON object matching the `SubjectiveEvent` schema.
    3.  **LLM Call & Parse**: Call the LLM and parse the JSON response into a `SubjectiveEvent` object.
*   **Output**: A `SubjectiveEvent` Pydantic model object. This model (defined in `modules.data_models.py`) includes:
    *   `timestamp: str`: When the event was perceived.
    *   `observer_id: str`: The character who perceived the event.
    *   `perceived_description: str`: The observer's *subjective interpretation* of the event.
    *   `inferred_actor: Optional[str]`: Who the observer *believes* was the actor.
    *   `inferred_target: Optional[str]`: Who/what the observer *believes* was the target.

### 3.3. Identifying Observers: `get_observers(factual_outcome: str, ground_truth_world_state: WorldState, event_location_id: Optional[str] = None) -> List[str]`

Before individual `SubjectiveEvent`s can be generated, the system needs to know *who* might have perceived the `factual_outcome`.

*   **Inputs**:
    *   `factual_outcome: str`: The objective description of what happened.
    *   `ground_truth_world_state: WorldState`: The world state *when the event occurred*.
    *   `event_location_id: Optional[str]`: The ID of the location where the event primarily took place.
*   **Process**:
    1.  **Prepare LLM Prompt**: Provide the LLM with:
        *   The `factual_outcome`.
        *   The `event_location_id` (if specified).
        *   A summary of all character locations from `ground_truth_world_state.character_states`.
        *   Instructions to analyze the nature of the event (e.g., a loud sound vs. a subtle visual cue), character proximity to the event, potential line of sight, and other sensory factors.
        *   Instructions to return a list of character IDs who likely perceived the event.
    2.  **LLM Call & Parse**: Call the LLM and parse its response (e.g., a JSON list of IDs or a comma-separated string) into a `List[str]` of character IDs.
*   **Output**: `List[str]`: A list of character IDs deemed to be observers of the event.

## 4. Data Flow Example: An Objective Event Becomes Subjective Memory

1.  **Action & Outcome**: Character A performs an action. `WorldAgent.apply_plan` determines the `factual_outcome` (e.g., "Character A shoves Character B, who stumbles."). The `ground_truth_world_state` is updated.
2.  **Identify Observers**: `PerspectiveFilter.get_observers` is called with the `factual_outcome` and `ground_truth_world_state`. It returns a list of character IDs who likely witnessed this (e.g., `["char_A", "char_B", "char_C"]`).
3.  **Generate Subjective Events**: For each observer in the list:
    *   `PerspectiveFilter.get_subjective_event(observer_id, factual_outcome, ...)` is called.
    *   **For Character A (Actor)**: LLM might generate `SubjectiveEvent(perceived_description="I firmly pushed B out of my way.")`.
    *   **For Character B (Target)**: LLM might generate `SubjectiveEvent(perceived_description="A suddenly attacked me! I barely kept my balance.")`.
    *   **For Character C (Bystander)**: LLM might generate `SubjectiveEvent(perceived_description="I saw A get aggressive and shove B.")`.
4.  **Store Subjective Memories**: Each generated `SubjectiveEvent` is passed to `MemoryManager.remember(observer_id, subjective_event_data, ...)`, creating a personal memory for each character.

## 5. Impact on Narrative and Gameplay

This layered approach to perception—from objective `WorldState` through `PerspectiveFilter` to subjective views and memories—is fundamental to FicWorld's design:

*   **Character Agency**: Characters make decisions based on their `SubjectiveWorldView`, not perfect information.
*   **Dynamic Relationships**: Misunderstandings arising from differing `SubjectiveEvent`s can strain or build relationships.
*   **Plot Complexity**: The same core event can ripple through the character network in diverse ways, creating multiple sub-narratives.
*   **Replayability & Emergence**: Small changes in initial conditions or LLM interpretations of perception can lead to vastly different story outcomes.

The `PerspectiveFilter` is thus not just a technical component but a core driver of the unique, character-centric storytelling FicWorld aims to achieve.
