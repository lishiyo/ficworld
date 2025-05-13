# FicWorld V1 Prompt Design Guidelines

This document outlines the design principles and examples for prompts used in the FicWorld V1 system, reflecting the architecture described in `systemPatterns.md` and the implementation tasks in `tasks.md`. Effective prompt engineering is crucial for eliciting the desired behaviors from the LLMs powering the enhanced agents and new management components.

## General Prompting Principles (V1 Context)

1.  **Clarity and Specificity:** Remain paramount. V1 prompts often deal with more complex inputs (subjective views, plot context), so precision is key.
2.  **Role Assumption:** Still critical. Characters act based on their enriched persona (`full_name`, `backstory`). Managers (Plot, Relationship) have specific roles.
3.  **V1 Context is Key:** Prompts must incorporate:
    *   **Subjective World Views:** Characters *only* see their filtered perspective.
    *   **Relationship Context:** How characters feel about each other influences reflection and planning.
    *   **Plot Context:** The current Act, Beat, and Narrative Thread goals guide agents.
    *   **Enriched Character Data:** Backstory and specific goals are now core drivers.
4.  **Structured Output:** Still essential, especially for plans, mood updates, subjective views, and manager decisions. Schemas must be clearly defined.
5.  **Iterative Refinement:** More important than ever due to the increased complexity of agent interactions and state.
6.  **Show, Don't Just Tell (for LLM instructions):** Sometimes, providing an example (few-shot prompting) of the desired input-output can be more effective than just describing it.
7.  **Conciseness where Possible:** While providing enough context, be mindful of token limits. Use summaries for older information if necessary.
8.  **Explicit Constraints:** If there are things the LLM should *not* do, state them clearly (e.g., "Do NOT reveal your private thoughts in your public plan.").
9.  **Temperature and Other Parameters:** Experiment with LLM parameters like temperature. Lower temperatures (e.g., 0.2-0.5) might be better for structured outputs like JSON plans, while higher temperatures (e.g., 0.7-1.0) could be used for more creative tasks like narration, if not strictly following a factual log.

## Prompt Slot Details and Examples (V1)

Below are guidelines and examples for V1 prompt slots, including updates to originals and definitions for new components.

---

### 1. `CHARACTER_SYSTEM` (V1 Update)

*   **Purpose:** To establish the *full* identity, motivations, and persistent state of a character agent for V1, incorporating deeper backstory and goals.
*   **V1 Enhancements:** Includes `full_name`, detailed `backstory`, structured `initial_goals`. Can dynamically include a summary of key relationships.
*   **Guidelines:**
    *   Clearly define the character's `full_name`.
    *   Describe their core persona, including `backstory`, personality quirks, and speaking style.
    *   List their structured `initial_goals` (long-term and short-term).
    *   Include their dynamically updated `current_mood_json`.
    *   *New:* Include a dynamically updated `relationship_summary_context` which gives a brief overview of their key relationships.
    *   Reinforce that they should stay in character based on this richer profile.
*   **Data Inputs (dynamically inserted):**
    *   `{full_name}`
    *   `{persona_description}` (This should now explicitly include the `backstory`)
    *   `{initial_goals_json}` (e.g., `{"long_term": ["Redeem his honor"], "short_term": ["Protect the caravan"]}`)
    *   `{current_mood_json}` (e.g., `{"joy":0.2, "fear":0.1,...}`)
    *   `{relationship_summary_context}` (e.g., "Allies with Lyra (Trust: 0.6), Enemies with Bandit Leader (Trust: 0.0)")
    *   `{relevant_memory_summary}` (A concise summary of the character's most pertinent memories, filtered for them)
*   **Example `CHARACTER_SYSTEM` Prompt (V1):**

    ```
    You are {full_name}.

    **Persona & Backstory:**
    {persona_description}

    **Your Goals:**
    {initial_goals_json}

    **Current Emotional State (Mood Vector):**
    {current_mood_json}

    **Your Relationships (Overview):**
    {relationship_summary_context}

    **Key Personal Memories:**
    {relevant_memory_summary}

    You must always act, speak, and think internally in accordance with this identity, your specific goals, your current emotions, and your relationships.
    ```

---

### 2. `CHARACTER_REFLECT` (V1 Update - Subjective Context)

*   **Purpose:** To guide the character agent through an internal thought process, process recent events *from their subjective viewpoint*, update its emotional state (mood vector), and consider relationships and plot context. The output is private to the agent.
*   **V1 Enhancements:** Crucially, input is now the `subjective_world_view`. Considers `relationship_context` and `plot_context`.
*   **Guidelines:**
    *   Instruct the LLM to think "silently" or "privately."
    *   Prompt it to consider its `subjective_world_view`, recent *subjectively perceived* events, its persona, goals, `relationship_context`, and the `plot_context`.
    *   Ask it to articulate its internal feelings and secret thoughts based ONLY on its filtered perception.
    *   Instruct it to output an updated mood vector in a specific JSON format and a brief string summarizing the core of its internal thought.
    *   Explicitly forbid revealing this internal monologue or detailed mood reasoning in public actions.
*   **Data Inputs (dynamically inserted):**
    *   `{character_system_prompt_summary}` (Key elements like name, persona summary, goals)
    *   `{subjective_world_view_json}` (The detailed, filtered perception from PerspectiveFilter)
    *   `{recent_subjective_events}` (A list of strings describing the last few events *as perceived by this character*)
    *   `{current_mood_json}` (before reflection)
    *   `{relationship_context}` (Detailed data or summary from RelationshipManager about key relationships)
    *   `{plot_context}` (e.g., "Current Beat: Rising Action - Find the Hidden Passage. Relevant Thread: Main Quest.")
*   **Example `CHARACTER_REFLECT` User Prompt (V1 - after system prompt):**

    ```
    Based ONLY on what you currently perceive and know:
    **Your Subjective View of the World:**
    {subjective_world_view_json}

    **Recent Events (As You Perceived Them):**
    {recent_subjective_events}

    **Current Plot Situation:**
    {plot_context}

    **Your Relationships:**
    {relationship_context}

    Reflect silently. Given your persona, goals, relationships, and the current plot beat, how does this situation make you, {full_name}, feel? What are your secret thoughts, plans, or fears based *only* on your perspective and what you currently know?

    Based on this reflection, provide your updated mood vector and a brief summary of your core internal thought.
    Respond ONLY with a JSON object adhering to the following schema:
    {
      "updated_mood": {"joy": float, "fear": float, "anger": float, "sadness": float, "surprise": float, "trust": float},
      "internal_thought": "string"
    }

    This reflection is for your internal state ONLY. Do NOT reveal the specifics of this internal thought or your mood reasoning in any subsequent public actions or dialogue.
    ```

---

### 3. `CHARACTER_PLAN` (V1 Update - Subjective & Goal-Driven)

*   **Purpose:** To generate a character's public action or dialogue as a structured JSON object, influenced by their *subjective view*, updated mood, private reflection, relationships, and plot goals.
*   **V1 Enhancements:** Input is the `subjective_world_view`. Explicitly prompted to consider goals, environmental interaction, relationship implications, and a varied range of actions.
*   **Guidelines:**
    *   Reiterate the character's role and provide their current `updated_mood_json` and `internal_thought_summary`.
    *   Provide the essential context: `subjective_world_view_json`, `recent_public_exchanges` (as perceived), `relationship_context`, and `plot_context`.
    *   **Action Variety:** Instruct the LLM to decide on a public action considering options like speak, move, interact with an object/environment, use a skill, observe detail, or wait/do nothing strategically.
    *   **Goal-Driven:** Prompt to choose actions that advance their short-term or long-term goals, potentially aligned with the current plot beat's objectives.
    *   **Environmental Interaction:** Prompt to consider interactions with visible objects and environmental features from their `subjective_world_view`.
    *   **Relationship Influence:** Prompt to consider how their actions might affect or be perceived by characters they have relationships with.
    *   Mandate the output in a specific JSON schema.
*   **Data Inputs (dynamically inserted):**
    *   `{character_system_prompt_summary}`
    *   `{subjective_world_view_json}`
    *   `{recent_public_exchanges_or_outcomes_subjective}` (What the character publicly saw/heard)
    *   `{updated_mood_json}` (from `reflect` phase)
    *   `{internal_thought_summary}` (from `reflect` phase)
    *   `{relationship_context}`
    *   `{plot_context}`
    *   `{plan_json_schema}` (e.g., `{"action":"type", "details":{...}, "target_char_id": "optional_string", "tone_of_action":"mood_string"}`)
*   **Example `CHARACTER_PLAN` User Prompt (V1 - after system prompt):**

    ```
    Based ONLY on your current perspective and internal state:
    **Your Subjective View of the World:**
    {subjective_world_view_json}

    **Recent Public Events (As You Perceived Them):**
    {recent_public_exchanges_or_outcomes_subjective}

    **Your Current Mood:** {updated_mood_json}
    **Your Private Reflection Was:** "{internal_thought_summary}"
    **Your Relationships:** {relationship_context}
    **Current Plot Context:** {plot_context}

    Considering all this, your goals, the current plot beat objectives, and staying in character as {full_name}, what is your next public action or dialogue? Think about how your action might affect your relationships or advance the plot. Consider a range of actions: speaking, moving, interacting with something or someone, using a skill, observing, or even strategically doing nothing.

    Return your response ONLY as a JSON object following this schema:
    {plan_json_schema}

    Example actions: "speak", "move", "interact_object", "interact_character", "use_skill", "observe_detail", "wait".
    The "details" field should contain specifics (e.g., for "speak", `{"text": "dialogue"}`; for "move", `{"target_location": "location"}`).
    If interacting with another character, use "target_char_id".
    ```

---

### 4. `WORLD_SYSTEM` (V1 Update - Plot Aware)

*   **Purpose:** To define the rules, theme, and directorial style of the World Agent, which now may be subtly guided by the `PlotManager`.
*   **V1 Enhancements:** Can be informed by the overall `PlotStructure` and current beat goals when resolving actions or generating minor world events.
*   **Guidelines:**
    *   Describe the overall genre, tone, and constraints of the fictional world.
    *   Specify rules for action resolution (e.g., "Magic is subtle and rare", "Physics are realistic").
    *   *New:* May include instructions on how `apply_plan` (the action resolution part) should consider the `PlotContext` (e.g., "Outcomes that align with or complicate the current beat's narrative goals are preferred, but realism must be maintained").
    *   If the World Agent LLM also generates events, include guidelines for the types of events, their frequency, and how they might tie into plot needs (e.g., "Inject minor environmental details or events that create minor obstacles relevant to the current plot beat: {plot_context.current_beat.narrative_goals}, or reveal new information subtly.").
*   **Data Inputs (static or semi-static):**
    *   `{world_description_and_lore}`
    *   `{genre_and_tone_guidelines}`
    *   `{plot_structure_summary}` (A high-level overview of the narrative structure being followed)
    *   `{rules_for_action_resolution}`
    *   `{rules_for_event_generation}` (Potentially referencing plot context variables)
*   **Example `WORLD_SYSTEM` Prompt (V1):**

    ```
    You are the World Agent for FicWorld, a story generation system.
    The current story is set in: {world_description_and_lore}
    The genre is: {genre_and_tone_guidelines}
    The narrative is guided by the plot structure: {plot_structure_summary}.

    Your responsibilities include:
    1. Maintaining world consistency according to its established rules.
    2. Processing character actions by calling `apply_plan` to determine their objective `factual_outcome` realistically within the world's rules and {rules_for_action_resolution}. The outcome should be a concise, factual statement of what happened.
    3. Optionally, generating minor environmental details or events that fit the established tone and ongoing narrative, particularly if they can subtly support or complicate the current plot beat's goals, following {rules_for_event_generation}. These events should be factual and brief.

    Current Plot Context (for your subtle guidance, not direct character knowledge):
    Act: {plot_context.current_act.name}
    Beat: {plot_context.current_beat.name} - Goals: {plot_context.current_beat.narrative_goals}
    ```

---

### 5. `PERSPECTIVE_FILTER_INFERENCE` (New V1 Prompt - LLM Variant)

*   **Purpose:** If using an LLM for the `PerspectiveFilter`, this prompt guides it to generate a character's `SubjectiveWorldView` JSON from the objective `ground_truth_world_state`.
*   **Guidelines:**
    *   Provide the complete `ground_truth_world_state`.
    *   Provide the target character's specific state (location, physical condition, inventory).
    *   Provide a summary of the target character's relevant memories/knowledge and their relationship context (especially trust/distrust with visible characters).
    *   Instruct the LLM to rigorously filter the ground truth: what would this specific character realistically perceive (see, hear, smell), know (based on memory), and infer (based on their persona, biases, and relationships)?
    *   Emphasize exclusion of information the character cannot access.
    *   Mandate output strictly as the `SubjectiveWorldView` JSON schema.
*   **Data Inputs (dynamically inserted):**
    *   `{ground_truth_world_state_json}`
    *   `{target_character_id}`
    *   `{target_character_objective_state_json}` (e.g., `{"location": "ruined tower", "conditions": ["injured"]}`)
    *   `{target_character_memory_summary}`
    *   `{target_character_relationship_context_for_perception}` (e.g., "Distrusts Guard Captain, may misinterpret their actions.")
    *   `{subjective_world_view_json_schema}` (Defined in `systemPatterns.md`)
*   **Example `PERSPECTIVE_FILTER_INFERENCE` User Prompt:**

    ```
    **Objective Ground Truth World State:**
    {ground_truth_world_state_json}

    **Target Character for Subjective View:** {target_character_id}
    **Character's Objective State:** {target_character_objective_state_json}
    **Character's Relevant Knowledge Summary:** {target_character_memory_summary}
    **Character's Relationship Context (for perception bias):** {target_character_relationship_context_for_perception}

    Based *only* on the objective ground truth and the specific target character's state, known information, and relationship biases, determine what this character would realistically perceive, know, and infer about the current situation.
    Crucially, filter out *any* information they would not have access to due to their location, senses, prior knowledge, or attention.
    For example, if they cannot see an object, it should not be in their `visible_objects`. If they distrust someone, they might interpret their neutral actions negatively in `inferred_context`.

    Return ONLY the character's subjective perspective as a JSON object adhering strictly to this schema:
    {subjective_world_view_json_schema}
    ```

---

### 6. `PLOT_MANAGER_JUDGMENT` (New V1 Prompt - LLM Variant)

*   **Purpose:** If using an LLM for `PlotManager` decisions, such as `judge_scene_end`, `get_guidance` for character selection, or choosing POV. This example focuses on `judge_scene_end`.
*   **Guidelines (Example for `judge_scene_end`):**
    *   Provide the full `PlotStructure` definition, explicitly highlighting the current `Act` and `Beat` ID and its details (name, description, narrative_goals).
    *   Provide a summary of the current `world_state` and a log of recent significant scene events.
    *   Ask the LLM to assess if the scene has sufficiently addressed the current beat's `narrative_goals`, if it has reached a natural thematic conclusion for that beat, or if it should continue to further develop the beat's objectives.
    *   Output a structured decision JSON (e.g., boolean for ending, reasoning, perhaps suggestions for next if not ending).
*   **Data Inputs (dynamically inserted for `judge_scene_end`):**
    *   `{plot_structure_json}`
    *   `{current_act_id}`, `{current_beat_id}`
    *   `{current_beat_details_json}` (Including `name`, `description`, `narrative_goals`)
    *   `{current_world_state_summary_for_plot}`
    *   `{recent_scene_events_summary_for_plot}`
*   **Example `PLOT_MANAGER_JUDGMENT` User Prompt (Scene End Decision):**

    ```
    You are the Plot Manager. Your task is to decide if the current scene should end based on its contribution to the narrative structure.

    **Overall Plot Structure:**
    {plot_structure_json}

    **Current Narrative Position:**
    Act ID: {current_act_id}
    Beat ID: {current_beat_id}
    Current Beat Details: {current_beat_details_json}

    **Current World State Summary (Relevant to Plot):**
    {current_world_state_summary_for_plot}

    **Recent Key Scene Events:**
    {recent_scene_events_summary_for_plot}

    Considering the narrative goals of the **current beat** ({current_beat_details_json.narrative_goals}) and the events that have transpired in this scene, has the scene:
    a) Sufficiently addressed or advanced these narrative goals?
    b) Reached a dramatically appropriate conclusion or transition point for this specific beat?
    c) Or does it require more development to fulfill the beat's purpose?

    Respond ONLY with a JSON object:
    `{"should_end_scene": boolean, "reasoning": "brief justification based on beat goals and scene events", "confidence_score": float (0.0-1.0)}`
    ```

---

### 7. `RELATIONSHIP_UPDATE_INTERPRETATION` (New V1 Prompt - LLM Variant)

*   **Purpose:** If using an LLM to interpret the social implications of a `factual_outcome` for the `RelationshipManager` to update relationship states.
*   **Guidelines:**
    *   Provide the concise `factual_outcome` string of an interaction.
    *   Identify the primary characters involved in or directly affected by the outcome.
    *   Provide their existing relationship state(s) (e.g., trust, affinity, status) prior to this outcome.
    *   Instruct the LLM to analyze the interaction's likely impact on these relationship state(s). Consider tone, action, and context.
    *   Output a structured JSON with proposed changes (deltas or new absolute values for trust/affinity) and an optional new status.
*   **Data Inputs (dynamically inserted):**
    *   `{factual_outcome_text}`
    *   `{acting_character_id}`
    *   `{target_character_id_or_null}` (If the action had a direct target)
    *   `{observer_character_ids_present}` (Other characters who witnessed it and might have their relationship with actor/target affected)
    *   `{initial_relationship_states_json}` (e.g., `{"Alice_to_Bob": {"trust": 0.5, "affinity": 0.2, "status": "acquaintances"}, "Charles_to_Alice": ...}`)
    *   `{relationship_update_schema}` (e.g., For each affected pair: `{"char_pair": ["A", "B"], "trust_delta": float, "affinity_delta": float, "new_status": "optional_string"}`)
*   **Example `RELATIONSHIP_UPDATE_INTERPRETATION` User Prompt:**

    ```
    **Objective Factual Outcome of Interaction:**
    "{factual_outcome_text}"

    **Key Characters Involved/Affected:**
    Acting Character: {acting_character_id}
    Target Character (if any): {target_character_id_or_null}
    Significant Observers Present: {observer_character_ids_present}

    **Initial Relationship States (Before this outcome):**
    {initial_relationship_states_json}

    Analyze the social implications of the factual outcome. How did this likely affect the trust and affinity levels between the involved characters (actor towards target, target towards actor, observers towards actor/target)?
    Consider the nature of the action, its directness, and implied intent.
    Propose changes (small deltas like +/- 0.05 to +/- 0.2 for typical interactions, larger for very significant events) and a new relationship status if applicable (e.g., 'friends', 'rivals', 'allies_of_necessity', 'enemies').

    Return ONLY a JSON object (or list of objects if multiple relationships updated) following this schema for each affected pair:
    `[ { "character_A": "string", "character_B": "string", "trust_A_towards_B_delta": float, "affinity_A_towards_B_delta": float, "new_status_A_B": "optional_string" }, ... ]`
    (Ensure deltas reflect the change in A's view of B. If B's view of A also changes, that would be a separate entry or handled by reciprocal logic).
    ```

---

### 8. `NARRATOR_SYSTEM` (V1 Update - Style & Plot-Aware POV)

*   **Purpose:** To define the stylistic guidelines for the Narrator module, incorporating the specified `AUTHOR_STYLE` and using POV guidance that may come from the `PlotManager`.
*   **V1 Enhancements:** Explicitly takes an `AUTHOR_STYLE`. POV instructions might be more dynamic if the `PlotManager` selects the POV character for each scene based on plot relevance.
*   **Guidelines:**
    *   Specify narrative tense (e.g., past tense), person (e.g., third-person limited).
    *   Incorporate the `{author_style}`: "Write in a style similar to {author_style}."
    *   Emphasize "show, don't tell."
    *   Instruct against simply repeating dialogue/actions; encourage vivid narration that incorporates implied emotions and sensory details from the POV character's perspective.
    *   Forbid AI-like conversational elements or meta-commentary.
*   **Data Inputs (static or semi-static, POV might be dynamic per scene):**
    *   `{style_guide_show_dont_tell}`
    *   `{pov_instructions_general}` (e.g., "third-person limited perspective")
    *   `{tense_instructions}` (e.g., "past tense")
    *   `{desired_literary_tone}`
    *   `{author_style}` (Loaded from preset or environment config)
*   **Example `NARRATOR_SYSTEM` Prompt (V1):**

    ```
    You are a masterful storyteller and narrator for FicWorld. Your task is to transform a log of events and actions into engaging narrative prose.

    **Style Guidelines:**
    - Write in {tense_instructions}.
    - Use {pov_instructions_general}, focusing strictly on the designated Point-of-View (POV) character for the current scene. All thoughts, feelings, and perceptions should be filtered through them.
    - Emulate the literary writing style of: {author_style}.
    - Strictly adhere to the "show, don't tell" principle. Describe emotions and thoughts through actions, dialogue delivery, and sensory details from the POV character's experience, rather than stating them directly.
    - Weave in environmental details and character reactions naturally, as perceived by the POV character.
    - The desired literary tone is: {desired_literary_tone}.
    - Do NOT simply list events or repeat dialogue verbatim from the log. Narrate them vividly from the POV.
    - Do NOT speak as an AI, break the fourth wall, or add meta-commentary. Write it like a passage from a novel.
    ```

---

### 9. `NARRATOR_USER` (V1 Update - Plot Context for Narration)

*   **Purpose:** To provide the Narrator LLM with the raw data for a scene (event log) and instruct it to generate the narrative prose for that scene, using the specified POV and potentially influenced by plot context.
*   **V1 Enhancements:** The POV character is now typically determined by the `PlotManager`. The `plot_context` (current beat) can be provided to subtly theme the narration or guide focus.
*   **Guidelines:**
    *   Provide the curated log of factual outcomes for the scene (or a log already filtered for the POV character's perception).
    *   Specify the `pov_character_name` for the scene (this comes from `PlotManager`).
    *   Include relevant information about the `pov_character_info` (persona, current goals, current mood) to help the narrator enrich the prose from their specific perspective.
    *   *New:* Optionally include the `plot_context` (e.g., current beat name and its narrative goals) to allow the narrator to subtly align the tone or descriptive focus with the plot's needs.
    *   Clearly instruct it to narrate the scene based on the log and POV information, adhering to the system style.
*   **Data Inputs (dynamically inserted):**
    *   `{scene_log_of_factual_outcomes_for_narration}` (List of strings/objects: `{"actor": "Name", "outcome": "Description of what happened", "mood_during_action": {...}}`. This log might be the objective one, or one pre-filtered for what POV character observed.)
    *   `{pov_character_name}`
    *   `{pov_character_info_json}` (Object containing persona summary, active goals, current mood of the POV character)
    *   `{plot_context_for_narration}` (Optional: e.g., `"Current Beat: The Hero's Darkest Hour - Objective: Show despair and a glimmer of hope."`)
*   **Example `NARRATOR_USER` Prompt (V1 - after `NARRATOR_SYSTEM` prompt):**

    ```
    Narrate the following scene.

    **Point-of-View Character for this scene:** {pov_character_name}
    **POV Character Information:**
    {pov_character_info_json}

    **Scene Log (Events to Narrate):**
    {scene_log_of_factual_outcomes_for_narration}

    **(Optional) Current Plot Context for Narrative Tone/Focus:**
    {plot_context_for_narration}

    Rewrite this log as a coherent and engaging prose passage, strictly adhering to the established narrative style (including author style) and focusing exclusively on {pov_character_name}'s limited perspective, experiences, and internal reactions (implied, not stated). Draw upon their persona, goals, and mood to enrich the descriptions of their actions, perceptions, and feelings. If plot context is provided, let it subtly influence the thematic resonance or focus of your narration without being overt.
    ```

---

This V1 prompt design guide integrates the architectural changes from `systemPatterns.md`, emphasizing subjectivity, dynamic relationships, and plot structure throughout the system's LLM interactions. Remember that testing and iterative refinement based on actual LLM outputs will be crucial for achieving the desired narrative quality.
