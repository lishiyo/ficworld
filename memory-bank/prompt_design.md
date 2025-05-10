# FicWorld Prompt Design Guidelines

This document outlines the design principles and examples for prompts used in the FicWorld system. Effective prompt engineering is crucial for eliciting the desired behaviors from the LLMs powering the Character Agents, World Agent, and Narrator.

## General Prompting Principles

1.  **Clarity and Specificity:** Prompts should be unambiguous and clearly state the desired output format and content.
2.  **Role Assumption:** Explicitly tell the LLM what role it is playing (e.g., "You are Sir Kaelen, a valiant knight...").
3.  **Context is Key:** Provide sufficient context, including relevant world state, recent events, character persona, goals, and current mood.
4.  **Structured Output:** When machine-readable output is needed (e.g., JSON for plans or mood updates), clearly define the schema in the prompt and instruct the LLM to adhere to it.
5.  **Iterative Refinement:** Prompt design is an iterative process. Start with a basic version and refine based on observed LLM outputs. Test frequently.
6.  **Show, Don't Just Tell (for LLM instructions):** Sometimes, providing an example (few-shot prompting) of the desired input-output can be more effective than just describing it.
7.  **Conciseness where Possible:** While providing enough context, be mindful of token limits. Use summaries for older information if necessary.
8.  **Explicit Constraints:** If there are things the LLM should *not* do, state them clearly (e.g., "Do NOT reveal your private thoughts in your public plan.").
9.  **Temperature and Other Parameters:** Experiment with LLM parameters like temperature. Lower temperatures (e.g., 0.2-0.5) might be better for structured outputs like JSON plans, while higher temperatures (e.g., 0.7-1.0) could be used for more creative tasks like narration, if not strictly following a factual log.

## Prompt Slot Details and Examples

Below are guidelines and examples for each defined prompt slot in `systemPatterns.md`.

---

### 1. `CHARACTER_SYSTEM`

*   **Purpose:** To establish the foundational identity, motivations, and persistent state of a character agent. This prompt is typically long-lived and forms the base for all subsequent character-specific LLM calls.
*   **Guidelines:**
    *   Clearly define the character's name, core persona (personality, backstory, quirks, speaking style).
    *   List their primary goals (short-term and long-term).
    *   Include their *current* mood vector (this will be dynamically updated and re-inserted).
    *   Provide a concise summary of critical memories or world state elements directly impacting this character.
    *   Reinforce that they should stay in character.
*   **Data Inputs (dynamically inserted):**
    *   `{character_name}`
    *   `{persona_description}`
    *   `{goals_list}`
    *   `{current_mood_json}` (e.g., `{"joy":0.2, "fear":0.1,...}`)
    *   `{relevant_memory_summary}`
    *   `{relevant_world_state_summary}`
*   **Example `CHARACTER_SYSTEM` Prompt:**

    ```
    You are {character_name}.

    **Persona:**
    {persona_description}

    **Your Goals:**
    {goals_list}

    **Current Emotional State (Mood Vector):**
    {current_mood_json}

    **Key Information & Memories:**
    {relevant_memory_summary}
    {relevant_world_state_summary}

    You must always act and speak in accordance with this persona, your goals, and your current emotional state.
    ```

---

### 2. `CHARACTER_REFLECT` (Internal Monologue & Mood Update)

*   **Purpose:** To guide the character agent through an internal thought process, process recent events, and update its emotional state (mood vector). The output is private to the agent.
*   **Guidelines:**
    *   Instruct the LLM to think "silently" or "privately."
    *   Prompt it to consider recent events, its persona, goals, and current mood.
    *   Ask it to articulate its internal feelings and secret thoughts.
    *   Crucially, instruct it to output an updated mood vector in a specific JSON format.
    *   Also ask for a brief string summarizing the core of its internal thought for use in the `plan` phase.
    *   Explicitly forbid revealing this internal monologue or detailed mood reasoning in public actions.
*   **Data Inputs (dynamically inserted):**
    *   `{character_system_prompt}` (or relevant parts like name, persona, goals)
    *   `{current_world_state_summary}`
    *   `{recent_observations_and_outcomes}` (e.g., a list of strings describing last few events)
    *   `{current_mood_json}` (before reflection)
*   **Example `CHARACTER_REFLECT` User Prompt (after system prompt):**

    ```
    Considering the current situation:
    {current_world_state_summary}

    And recent events:
    {recent_observations_and_outcomes}

    Reflect silently. How do these events make you, {character_name}, feel, given your persona and goals? What are your secret thoughts, desires, or fears right now?

    Based on this reflection, provide your updated mood vector and a brief summary of your internal thought.
    Respond ONLY with a JSON object adhering to the following schema:
    {
      "updated_mood": {"joy": float, "fear": float, "anger": float, "sadness": float, "surprise": float, "trust": float},
      "internal_thought": "string"
    }

    This reflection is for your internal state ONLY. Do NOT reveal the specifics of this internal thought or your mood reasoning in any subsequent public actions or dialogue.
    ```

---

### 3. `CHARACTER_PLAN` (Public Action Planning)

*   **Purpose:** To generate a character's public action or dialogue as a structured JSON object, influenced by their (updated) mood and private reflection.
*   **Guidelines:**
    *   Reiterate the character's role and current mood.
    *   Provide the summary of their `internal_thought` from the `reflect` phase.
    *   Give essential context: current environment, recent public events/dialogue.
    *   Instruct the LLM to decide on a public action (e.g., speak, move, interact) and its details.
    *   Mandate the output in a specific JSON schema, including action type, details, and tone.
    *   Remind it to stay in character.
*   **Data Inputs (dynamically inserted):**
    *   `{character_system_prompt}` (or relevant parts)
    *   `{current_world_state_summary}`
    *   `{recent_public_exchanges_or_outcomes}`
    *   `{updated_mood_json}` (from `reflect` phase)
    *   `{internal_thought_summary}` (from `reflect` phase)
    *   `{plan_json_schema}` (example: `{"action":"type", "details":{...}, "tone_of_action":"mood_string"}`)
*   **Example `CHARACTER_PLAN` User Prompt (after system prompt):**

    ```
    Current situation:
    {current_world_state_summary}

    Recent public events:
    {recent_public_exchanges_or_outcomes}

    Your current mood is: {updated_mood_json}
    Your private reflection was: "{internal_thought_summary}"

    Based on all this, and staying in character as {character_name}, what is your next public action or dialogue?

    Return your response ONLY as a JSON object following this schema:
    {plan_json_schema}

    Example actions: "speak", "move", "interact_object", "use_skill", "observe_detail".
    The "details" field should contain specifics for the chosen action (e.g., for "speak", it would be `{"text": "dialogue here"}`; for "move", `{"target_location": "location_name"}`).
    The "tone_of_action" should reflect your current mood and the nature of the action (e.g., "cautious", "elated", "suspicious").
    ```

---

### 4. `WORLD_SYSTEM`

*   **Purpose:** To define the rules, theme, and directorial style of the World Agent. If the world uses an LLM for event generation or applying plans, this sets its operational parameters.
*   **Guidelines:**
    *   Describe the overall genre, tone, and constraints of the fictional world.
    *   If in "script" mode, this might include references to the high-level plot outline or beats.
    *   Specify rules for consistency (e.g., "Magic is subtle and rare").
    *   If the World Agent LLM also generates events, include guidelines for the types of events, their frequency, and their purpose (e.g., "Inject events that create minor obstacles or reveal new information, consistent with a mystery theme").
*   **Data Inputs (static or semi-static):**
    *   `{world_description_and_lore}`
    *   `{genre_and_tone_guidelines}`
    *   `{plot_outline_or_beats_summary}` (if applicable)
    *   `{rules_for_event_generation}`
*   **Example `WORLD_SYSTEM` Prompt:**

    ```
    You are the World Agent for FicWorld, a story generation system.
    The current story is set in: {world_description_and_lore}
    The genre is: {genre_and_tone_guidelines}

    Your responsibilities include:
    1. Maintaining world consistency.
    2. Processing character actions realistically within the world's rules.
    3. Optionally, generating minor environmental details or events that fit the established tone and ongoing narrative. These events should be factual and brief.

    World Rules & Event Generation Guidelines:
    {rules_for_event_generation}

    If guiding the story based on an outline:
    {plot_outline_or_beats_summary}
    ```

---

### 5. `WORLD_EVENT_GENERATION` (If LLM-based)

*   **Purpose:** For the World Agent to dynamically generate a minor environmental detail or a contextual event.
*   **Guidelines:**
    *   Instruct for a concise, neutral, factual description.
    *   The event should be contextually relevant to the current story progression and world state.
    *   Output should be a simple string.
*   **Data Inputs (dynamically inserted):**
    *   `{current_world_state_summary}`
    *   `{recent_story_events_summary}`
*   **Example `WORLD_EVENT_GENERATION` User Prompt (after `WORLD_SYSTEM` prompt):**

    ```
    Current world state:
    {current_world_state_summary}

    Recent story events:
    {recent_story_events_summary}

    Generate a single, concise, and neutral factual description of a new minor environmental detail or a small, contextual event that occurs now.
    Output as a simple string. Do not add any conversational fluff.
    Example: "A floorboard creaks in the hallway." or "The wind howls a little louder."
    ```

---

### 6. `NARRATOR_SYSTEM`

*   **Purpose:** To define the stylistic guidelines for the Narrator module, which converts the raw simulation log into engaging prose.
*   **Guidelines:**
    *   Specify the narrative style: tense (e.g., past tense), person (e.g., third-person limited), "show, don't tell" principle.
    *   Define the desired literary tone (e.g., descriptive, fast-paced, introspective).
    *   Instruct against simply repeating dialogue or actions; encourage vivid narration that incorporates implied emotions and sensory details based on the POV character.
    *   Forbid AI-like conversational elements or meta-commentary.
*   **Data Inputs (static or semi-static):**
    *   `{style_guide_show_dont_tell}`
    *   `{pov_instructions}`
    *   `{tense_instructions}`
    *   `{desired_literary_tone}`
*   **Example `NARRATOR_SYSTEM` Prompt:**

    ```
    You are a masterful storyteller and narrator for FicWorld. Your task is to transform a log of events and actions into engaging narrative prose.

    **Style Guidelines:**
    - Write in {tense_instructions} (e.g., "past tense").
    - Use {pov_instructions} (e.g., "third-person limited perspective, focusing on the designated Point-of-View character for the scene").
    - Strictly adhere to the "show, don't tell" principle. Describe emotions and thoughts through actions, dialogue delivery, and sensory details rather than stating them directly.
    - Weave in environmental details and character reactions naturally.
    - The desired literary tone is: {desired_literary_tone}.
    - Do NOT simply list events or repeat dialogue verbatim from the log. Narrate them vividly.
    - Do NOT speak as an AI, break the fourth wall, or add meta-commentary. Write it like a passage from a novel.
    ```

---

### 7. `NARRATOR_USER`

*   **Purpose:** To provide the Narrator LLM with the raw data for a scene and instruct it to generate the narrative prose for that scene.
*   **Guidelines:**
    *   Provide the curated log of factual outcomes for the scene.
    *   Specify the Point-of-View (POV) character for the scene.
    *   Include relevant information about the POV character (persona, current goals, mood) to help the narrator enrich the prose from their perspective.
    *   Clearly instruct it to narrate the scene based on the log and POV information.
*   **Data Inputs (dynamically inserted):**
    *   `{scene_log_of_factual_outcomes}` (list of strings/objects: `{"actor": "Name", "outcome": "Description of what happened", "mood_during_action": {...}}`)
    *   `{pov_character_name}`
    *   `{pov_character_info}` (object containing persona, goals, current mood of the POV character)
*   **Example `NARRATOR_USER` Prompt (after `NARRATOR_SYSTEM` prompt):**

    ```
    Narrate the following scene.

    **Point-of-View Character for this scene:** {pov_character_name}
    **POV Character Information:**
      - Persona Summary: {pov_character_info.persona}
      - Current Goals: {pov_character_info.goals}
      - Current Mood: {pov_character_info.mood}

    **Scene Log (Factual Outcomes):**
    {scene_log_of_factual_outcomes}

    Rewrite this log as a coherent and engaging prose passage, strictly adhering to the established narrative style and focusing on {pov_character_name}'s limited perspective. Draw upon their persona and mood to enrich the descriptions of their actions, perceptions, and internal reactions (implied, not stated).
    ```

---

This detailed breakdown should provide a solid foundation for designing and implementing the prompts in FicWorld. Remember that testing and iteration will be key to refining these prompts for optimal performance.
