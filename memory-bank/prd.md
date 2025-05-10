# FicWorld: An Autonomous Multi-Agent StoryWriter

Goal: To create coherent short stories and whole books through AI agents that stand in for characters. **Each character is an autonomous agent** with its own persona, memories, **emotions, capacity for private reasoning,** motivations, and behaviors. Rather than a single omniscient narrator, the narrative emerges from the **interactions among these character agents** within a shared world. A separate *world-building agent* (or "world agent") sets the scene and enforces global consistency (the environment, events, and overall plot constraints), but direct control over the story is minimized. This approach lets characters "take on a life of their own," aligning with the idea that once characters and worlds are established, stories should unfold from their dynamics.

MVP goal:
Build a system that can generate coherent short stories → full novels through emergent interaction of autonomous character agents **possessing emotion, memory, and private reasoning capabilities.** We take BookWorld's proven design (role agents + world agent + narrator) and adapt it for a lean, easily-swappable Python stack running on OpenRouter models (default: DeepSeek R1).

## Tech Stack

Python
OpenRouter - default to Deepseek R1, but should be easy to swap to any LLM model like Gemini 2.5 Pro

We will start with a simple custom architecture for quick prototyping and clarity. This lets us define the storytelling loop and prompt patterns explicitly. We should still draw inspiration from CAMEL's design (roles, memory, etc.) and even integrate CAMEL later for scaling. CAMEL would be the next choice if we want a framework – it's tailored for agent societies and is compatible with OpenRouter out-of-the-box.

We should design this project in a way that it is easy to swap to using another framework like CAMEL. CAMEL's pros include:
- High-level abstractions like AgentSociety for defining agent roles and interactions, built-in memory management, and easy model integration (including DeepSeek via OpenRouter)
- Cons – Current high-level APIs (e.g. RolePlaying) are mainly for two-agent role-play; using it for four characters plus a world agent may require custom orchestration or using lower-level society tools.

Refer to the directory `bookworld-original` to see an implementation we can use as reference.

## System Architecture Overview

Read [systemPatterns](./systemPatterns.md) for detail.

The system will consist of several components orchestrating a multi-agent story simulation:

**Character Agents (4)** – Autonomous characters each with a distinct persona, goals, **mood (represented as an emotional vector), and a two-step thinking process involving private reflection (`reflect()`) before public action planning (`plan()`).** They "live" in the story world and decide actions or dialogue in each turn based on their personality, current emotional state, and objectives.

**World Agent (1)** – An agent representing the environment and plot events. It sets the scene, enforces world rules, and occasionally injects new events or challenges that drive the narrative forward.

**Narrator Module** – Not exactly a character in the story, but a module (using the LLM) that observes the raw interactions (dialogue/actions from character and world agents) and rewrites them into narrative prose. The narrator produces the story text in a show-don't-tell, limited POV style, making it engaging and coherent for the reader.

**LLM Interface** – An abstraction layer to call the language model (DeepSeek R1 via OpenRouter) for any agent that needs to generate text. This ensures model calls are handled uniformly and makes it easy to swap the LLM (e.g., switching to GPT-4 or another model by changing one config).

**Memory & World State** – A storage mechanism to keep track of what has happened (agent memories) and the current state of the world (locations, objects, time, etc.). This ensures consistency as the story progresses, especially as context length grows.

All these components interact during simulation rounds. The world agent provides context, character agents act and react, and the narrator turns those actions into the story narrative. The LLM (DeepSeek R1) is the engine behind each agent's decision and the narrator's prose, guided by prompts that shape its outputs.


## Character Agents: Persona, Goals, Memory, Mood

Each character agent can be represented as a Python class (or a config + functions) encapsulating its identity and state:

**Persona/Role:** A description of who the character is – their backstory, personality, and demeanor. This will be baked into the agent's system prompt or initial instructions. For example, a knight character's persona might include bravery, loyalty, and old-fashioned speech patterns. The persona effectively acts as the agent's "role" definition

**Goals:** Each character has one or more objectives or motivations driving them. Goals can be long-term ("protect the kingdom") and short-term ("find shelter for the night"). These will influence how the agent responds each turn. We can include the goals in the prompt (e.g., reminding the agent "Your goal is to reunite with your lost sister").

**Mood/Emotion:** The agent's current emotional state is represented by a **mood vector** (e.g., `{joy: 0.2, fear: 0.1, anger: 0.0, sadness: 0.1, surprise: 0.0, trust: 0.6}`). This vector is dynamically updated during the agent's private `reflect()` phase based on their internal monologue, interpretation of events, and progress towards goals. The mood vector influences their tone, decision-making in the `plan()` phase, and how they retrieve memories (see Emotional RAG below).

**Memory:** The agent's memory consists of knowledge of past events, observations, and interactions. For the MVP, especially if using a model with a very large context window (e.g., Gemini 2.5 Pro), the system can start by sending a significant portion of recent history or even the entire relevant history for short stories to the LLM. 
Crucially, each significant memory entry will be stored not only with its content (and embedding for retrieval) but also with the **agent's mood vector at the time the memory was encoded.** This enables "Emotional RAG" (Retrieval Augmented Generation), where an agent's current mood can be used to preferentially retrieve memories that are emotionally congruent, in addition to semantic relevance. In a more advanced version, particularly for longer narratives, this will evolve to use a dedicated `MemoryManager` employing time-weighted retrieval and potentially a vector database (see "Memory and World State Management" section for details). CAMEL-like designs emphasize memory so agents can reference past interactions and we'll do the same.

**Defining the Agent (Two-Step Thinking: `reflect()` and `plan()`):** Character agents employ a two-step thinking process each turn:
1.  **`reflect(world_state, observations)` Method (Inner Monologue & Mood Update):** Before deciding on a public action, the agent first engages in a private reflection. This step involves an internal monologue where the agent processes the current `world_state`, recent `observations`, and its own memories. This reflection is guided by a specific prompt (e.g., `CHARACTER_REFLECT`) and aims to: 
    *   Interpret the situation from its unique perspective.
    *   Consider its goals and current emotional state.
    *   Formulate private thoughts or intentions (which are *not* directly logged as part of the story's event log).
    *   Update its internal mood vector based on this reflection. The output of `reflect()` is primarily the updated mood and potentially a concise summary of key internal insights relevant for the next step.
2.  **`plan(world_state, observations, private_reflection_summary)` Method (Public Action Planning):** Following reflection, the agent formulates a public action. This method constructs a prompt (e.g., `CHARACTER_PLAN`) combining:
    *   The agent's persona and goals.
    *   A summary of relevant `world_state` and recent events.
    *   The agent's now-updated mood vector and key insights from the `private_reflection_summary`.
    *   An instruction to respond in character, deciding on an action or dialogue, and to return the output as a structured JSON object. The prompt will explicitly include the target JSON schema (e.g., `{"action":"speak", "text": "..."}` or `{"action":"move", "location":"new_place", "emotion_in_action": "wary"}`).

When `plan()` is called, it sends this prompt to the LLM and returns the LLM's structured JSON output. This public plan is then passed to the `WorldAgent` for processing. This two-step process allows for more nuanced and psychologically grounded characters, as their external actions are fueled by an internal emotional and cognitive state.

Each character agent operates similarly, ensuring they behave according to their personality, current emotions, and objectives.

### World Agent: Environment and Event Simulation

The world agent is responsible for the dynamic environment of the story. It can be implemented as a special agent or just a set of functions that update the scene:

**Setting the Scene:** At the start of the story or each scene, the world agent provides a description of the environment. For example, it might describe the location ("a dark forest on a stormy night"), time of day, and any background events ("wolves howl in the distance"). This context is fed into the prompts for character agents so they know what's happening around them.

**Applying Character Plans:** A crucial role of the World Agent is processing the structured JSON `plan` (the *public* action) submitted by a Character Agent. It does not have access to the character's private `reflect()` step. This involves an `apply_plan(plan, character_state, world_state)` method (or similar) with the following responsibilities:
1.  **Validate Feasibility:** Check if the planned action is possible given the `character_state` and current `world_state` (e.g., does the character have the item they want to use? Is the target location reachable?).
2.  **Modify Plan (If Necessary):** The World Agent might alter the plan based on world rules or hidden information (e.g., an attempt to open a door might be modified to "fails because it's magically sealed").
3.  **Update World State:** Modify the `world_state` based on the successful (or modified) execution of the plan (e.g., character's location changes, an item is consumed, a world variable is updated).
4.  **Generate Factual Outcome:** Create a concise, factual description of what actually happened as a result of the plan (e.g., "Sir Rowan moves to the old library." or "Briar attempts to pick the lock, but the mechanism is rusted shut."). This outcome is logged and becomes a key input for the Narrator.
5.  **Trigger Reactive Events:** The outcome of an action might trigger further reactive events or consequences in the world (e.g., opening a noisy door might alert nearby guards).

**Injecting Events:** The world agent can occasionally introduce new events or challenges. Initially, event injection can be driven by a predefined JSON list of potential events, which could even be extracted from existing story structures to provide some narrative scaffolding. As a more advanced option, the `WorldAgent` could also leverage an LLM to dynamically generate contextually relevant events based on the current story progression and `world_state`. These events will affect characters' decisions and moods. The injection can be done every few turns or when a certain condition is met (perhaps randomly or according to a simple plot script if not using dynamic LLM generation).

**World State Tracking:** It maintains a state representation of the world – locations of characters, inventory of important objects, time progression, etc. This state can be a simple dictionary or custom class (e.g., world_state = { "location": "forest", "weather": "rainstorm", "nearby_creatures": ["wolves"] }). After each turn, the world state might be updated (if a character starts a fire, weather might change to clear if the fire magically stops the rain, etc.).

**Consistency and Rules:** The world agent can enforce simple physics or story logic. For example, if a character tries to do something impossible (like see in complete darkness without a light), the world agent's next update can correct or highlight that ("it's too dark to see clearly"). This keeps the narrative coherent.

In practice, the world agent could be an LLM as well: given the current state, it could generate a descriptive update each round ("The rain intensifies, and lightning strikes a nearby tree."). However, to start minimally, you might script the world events or use random draws for events. If using the LLM for this, you'd give it a prompt like "You are the world and narrative engine. Describe any new events happening in the environment given the current state and recent actions, in a neutral factual way." The world agent's outputs become part of the context for the next round.

## Narrator Module: Narrative Rendering

The narrator module takes the raw simulation outputs (the dialogue/actions from the character agents and the world agent's descriptions) and rewrites them into a polished story form. This is where we enforce the "show, don't tell" and limited POV style:

**Show, Don't Tell:** The narrator should convert factual or blunt statements into vivid descriptions. For example, if a character agent output was: Alice (agent): "I feel scared of the dark forest.", the narrator might rewrite this as prose: Alice's heart hammered in her chest as she peered into the pitch-black forest, fingers trembling on the hilt of her sword. This conveys the fear through description and action rather than explicitly saying "she is scared."

**Limited POV:** We choose a perspective (usually one character per scene) and have the narrator describe events only through what that character could perceive. If the POV is Alice's, the narrator will detail Alice's thoughts, feelings, and sensory impressions, but won't mention another character's hidden thoughts. This makes the story feel grounded and personal. We can decide the POV character for each scene (perhaps rotate among the protagonists or stick to one main hero).

**Narration Process:** After each simulation round or scene, the system gathers a curated log of *applied* actions and events – essentially, the factual outcomes generated by the `WorldAgent` after processing character `plan`s (the "what" happened). This log is then fed into the narrator prompt. 
To provide richer narration that captures the "why" behind actions, the Narrator also needs access to relevant character information for the current scene or POV character, such as their persona, active goals, and current mood. 
The prompt would include a system message with guidelines (e.g., "You are a narrator writing a story. Use past tense, third-person limited to [Character Name]'s perspective, and a descriptive 'show, don't tell' style. Do not simply repeat the dialogue; instead narrate it vividly, drawing on your understanding of the character's motivations and feelings."). The user message might then list the raw factual outcomes. The narrator (as the LLM) then produces a narrative paragraph or two that retells those events in flowing story prose, enriched by its understanding of the character context.

**Incremental Story Output:** The narrator's output can be appended to a growing story text. After each scene, we accumulate the narrator's paragraphs. This is what a reader would see as the story. The intermediate agent dialogue or world state dumps would not be shown to the end user, only the narrator's crafted narrative.

By separating narrator duties, we ensure the final story is cohesive and stylistically consistent, rather than a disjointed chat log. Prompt engineering is key here – the narrator's system prompt should include style instructions (e.g., focus on sensory details, emotions through actions, maintain the character's voice in dialogue, etc.). You might also give the narrator examples of the desired style if needed (few-shot examples of "tell vs show" rewrites).

**LLM Integration and Model Abstraction**

We will use DeepSeek R1 via OpenRouter as the language model for all agents initially. To keep the design flexible, it's wise to create an abstraction layer for model calls:

OpenRouter API: OpenRouter allows access to various models (including DeepSeek R1) through an OpenAI-compatible API endpoint. We can use an OpenAI Python client (by pointing it to OpenRouter's URL and API key) or just do requests calls. This means our code can call openai.ChatCompletion.create(...) with the appropriate model name (e.g., deepseek/deepseek-r1:free) and API key, and OpenRouter will handle it. By isolating this in a module (say models.py or a helper function), we can easily swap the model name or endpoint.

Model Abstraction: Define a function like generate_response(prompt_messages, model="deepseek-r1") that wraps the API call. All agents and the narrator will use this function. It takes a list of messages (in OpenAI format: system + conversation messages) and returns the LLM's reply. Internally, this could be implemented with OpenAI's SDK or HTTP calls to OpenRouter.

Swapping Models: Because we use a generic interface, switching to another model (GPT-4, Anthropic Claude, etc.) later is simple – just change the model name or route in one place. The prompts and logic remain the same. This fulfills the "clean abstraction to allow easy swapping of models" requirement.

Libraries Needed: If using OpenRouter via OpenAI API compatibility, the openai Python package can be used (set openai.api_base to https://openrouter.ai/api/v1 and supply the key). Alternatively, use requests to POST to OpenRouter's endpoints. In addition, we will likely use standard packages like dataclasses (to define agent data structures) and perhaps typer or argparse if we want a CLI for the script. For now, focus on core functionality: ensure the OpenRouter call works with the provided model.

By handling all LLM interactions in one place, we also make it easier to add features like logging or cost tracking for the API calls, or caching responses during development.

### Simulation Orchestration: Turns and Scenes

The orchestration logic controls how agents interact turn by turn, and how the story transitions between scenes:

**Initialization:** The world agent sets up the initial scene (environment description, initial world state). Each character agent is initialized with their persona, goals, starting_mood vector, and any prior knowledge (which may be none for a fresh story).

**Turn Loop:** In each turn, agents take actions one after another, influenced by what happened earlier in the turn:

1.  World Context Update: (Optional each turn) The world agent may provide an update or minor event at the start of the turn (e.g., "the wind picks up."). This ensures the environment remains dynamic even if no big event occurs.

2.  Character Actions: Each character agent (`actor`) gets a chance to act or speak. We decide an order – possibly fixed or context-driven. In each sub-turn:
    *   Gather context: the `world_state`, last narrator output or last raw actions/outcomes, plus the agent's memory (retrieved potentially with emotional context).
    *   **`private_reflection = actor.reflect(world_state, memory_context)`:** The actor performs its internal monologue, updating its mood vector and forming private insights.
    *   **`public_plan = actor.plan(world_state, memory_context, private_reflection)`:** The actor, influenced by its reflection and updated mood, formulates a structured JSON plan for its public action.
    *   **`outcome = world_agent.apply_plan(public_plan, actor.state, world_state)`:** The `WorldAgent` processes this `public_plan`, updates the `world_state`, and logs the factual `outcome`.
    *   **`memory.remember(actor, outcome, mood=actor.current_mood)`:** The actor's memory is updated with the `outcome`, storing their `current_mood` vector alongside it.
    *   Other agents may observe the `outcome` to inform their own reflections and plans.

3.  World Agent Events: After characters act, the world agent might react to their collective actions or inject a pre-scripted/dynamically generated event. For example, if characters made a lot of noise, the world agent might introduce alerted guards. This can be done every turn or only when needed.

4.  Narration: Once a round of all agents acting (and any immediate world reactions) is complete, we have a collection of interactions for that time step. Now the narrator module is invoked to turn these into a narrative passage. The input to the narrator is the curated log of factual `outcome`s.

5.  Story Accumulation: Append the narrator's output to the story text. The narrator's output can also be fed back into the agents' memories as a summarized "this is what just happened."

**Scene Transitions:** A scene might consist of several turns. We define a condition for transitioning to a new scene or chapter (e.g., after N turns, a specific plot point reached, or if `world_agent.judge_scene_end(log)` returns true). At a scene break:
*   We might change the POV character for narration.
*   Relocate characters (update `world_state` significantly).
*   **`memory.summarise_scene(scene_number, log_of_outcomes)`:** The `MemoryManager` (potentially with Narrator assistance) can create a summary of the just-concluded scene to aid long-term memory and context management.
*   The `log_of_outcomes` for the completed scene is cleared or archived.

**Stopping Criteria:** The simulation could run for a fixed number of scenes or until a certain goal is achieved (maybe one of the character's main goals is reached, or a natural story climax occurs). Also, incorporate a safety break: if the story starts looping or the LLM outputs go off track, the loop can terminate after a max number of turns with a warning.

This orchestrated cycle ensures that each agent contributes to the evolving storyline and that their interactions are turned into a coherent narrative at regular intervals. You could implement this loop in main.py as straightforward for loops and function calls. Using an event loop or more complex scheduler isn't necessary for a simple prototype.

## Prompt Engineering Patterns

Crafting effective prompts is crucial to make sure agents behave believably and the narrator writes in the desired style:

**Character Agent Prompts (Two-Stage):**
1.  **`CHARACTER_REFLECT` (Internal Monologue & Mood Update):**
    *   **System Message:** "You are [Character Name]. This is a private reflection moment. Consider the recent events: [summary of recent observations/outcomes]. How do these make you feel? What are your secret thoughts, desires, or fears right now, given your persona: [persona summary] and goals: [goals list]? Based on this, provide an updated mood vector as JSON (e.g., `{"joy":0.1, "fear":0.7, ...}`), and a brief internal thought. Do NOT reveal this internal thought or specific mood reasoning in any public actions. This is for your internal state only."
    *   **User Message (Prompt):** "Reflect on the current situation and update your internal state."
    *   *Expected LLM Output for `reflect()`: A JSON object containing the updated mood vector and a short string for an internal thought, e.g., `{"updated_mood": {"joy":0.1,...}, "internal_thought": "I really don't trust that shadowy figure..."}`.*

2.  **`CHARACTER_PLAN` (Public Action Planning):**
    *   **System Message for agent:** "You are [Character Name], a fictional character in a story. Persona: [brief description of personality and background]. Goals: [list of goals]. Your current Mood is: [current mood vector]. Your recent private reflection was: [summary of internal_thought from `reflect()`]. Based on all this, you will decide your next public action or dialogue in the story, staying in character. Return your response as a structured JSON object following this schema: `{"action":"type_of_action", "details":{...}, "tone_of_action": "[e.g., cautious, angry, joyful]"}`.”
    *   **Context message(s):** Include the relevant world description ("The scene: [environment detail]"), and perhaps the last few public actions/outcomes from other characters ("Earlier this turn: [Other Character] did XYZ resulting in [Outcome]."). This gives situational awareness for the public plan.
    *   **User message (prompt):** A direct instruction or question to prompt action, e.g., "Based on the situation, your persona, your current mood, and your private reflection, what is your public `plan()`?"

This two-stage structure guides the LLM to first establish an internal state (`reflect`) and then produce a public, structured JSON `plan` influenced by that internal state. The narrator later will turn any applied actions and dialogue into narrative form.

**World Agent Prompt:** If the World Agent uses an LLM for dynamic event generation, its system prompt might be: "You are the world and setting of the story. You describe environment changes and outcomes of actions, or generate new contextual events." Provide the current state as context. Then a prompt like: "Given the recent actions and current `world_state`, describe any immediate outcome or generate a new event. Return event descriptions as neutral facts."

**Narrator Prompt:** The narrator's prompt is the most creative. A possible structure:
**System message:** "You are a storyteller narrating a fiction scene. Write in past tense, third person limited perspective (focused on [Character]'s POV). Use a 'show, don't tell' style with vivid sensory details and emotions implied through actions and dialogue. Do not enumerate events or speak as an AI; write it like a novel."
**User message:** Provide the raw log of the scene, e.g., a bullet list or script:
[World] The forest is dark and quiet.
[Alice] says "We should find shelter."
[Bob] lights a torch.
... etc.
Then: "Narrate this scene in a coherent paragraph:"

With this, the LLM should transform the script into flowing prose. We might include an example in the prompt (few-shot) of a tiny script and a narrated version, to reinforce the style.

Few-shot Examples: Provide one or two examples of converting telling to showing could help.

Token Limits: Keep prompts concise to avoid hitting context limits. Use summaries for older events. For example, an agent's persona can be a short paragraph, not pages of backstory, otherwise the prompt becomes too large. Similarly, pass only relevant recent events to each agent. However, if we use Gemini 2.5 Pro we will have a large context window.

Iterative Refinement: You might need to tweak these prompts after testing. If a character starts going out of character or the narrator writes in an expository way, refine the instructions. Prompt engineering is an iterative process – start simple, then add constraints or examples as needed.

By establishing these patterns, we ensure each agent and the narrator LLM knows its role and style. This approach mirrors how multi-agent frameworks structure roles (e.g., CAMEL's role definitions for identity and behavior) but here we manually design the prompts for our story needs.

## Memory and World State Management

Even a short story can produce a lot of information. We need to manage what each agent "remembers" and how the world state is updated:

**Agent Memory:** As mentioned in the Character Agents section, the MVP approach, especially with large context window models, might involve sending a significant portion of recent history. Each agent stores memories of events, observations, and outcomes. Critically, **each memory entry is stored with the agent's mood vector at the time of encoding.** This is foundational for Emotional RAG. For scalability and more complex narratives, a dedicated `MemoryManager` is planned. Before an agent `reflect`s and `plan`s, relevant memories are retrieved and included in its context. In code, `CharacterAgent` might have `self.memory` (managed by `MemoryManager`) and methods like `remember(event, current_mood)` and `recall(query, current_mood)`.

**Long-Term Memory Extension (Emotional RAG):** To support longer narratives and prevent loss of crucial information, the `MemoryManager` will incorporate a robust long-term memory (LTM) strategy, centered around **Emotional RAG**. This involves:
*   **Time-Weighted Retrieval:** Prioritizing more recent events, potentially combined with a decay factor for older memories unless they are marked as highly significant.
*   **Vector Database with Emotional Context:** Storing past events/observations not just with their semantic embeddings but also with the **mood vector** of the agent at the time the memory was formed.
*   **Emotional RAG Retrieval Logic:** When an agent needs to recall memories (e.g., during its `reflect` phase), the `MemoryManager.retrieve(query, current_mood_vector)` function will be used. This function will rank potential memories based on a combination of:
    *   **Semantic Similarity:** e.g., cosine similarity between the embedding of the `query` (or current situation) and the embeddings of stored memories.
    *   **Emotional Congruence:** e.g., cosine similarity or dot product between the agent's `current_mood_vector` and the `mood_vector` stored with each memory. Events experienced in a similar emotional state to the current one will be prioritized.
    The final ranking could be a weighted sum of these two scores (e.g., `score = (w_semantic * semantic_sim) + (w_emotion * mood_sim)`).
*   A library like Mem0 ([https://github.com/mem0ai/mem0](https://github.com/mem0ai/mem0)) is being considered for its specialized features for scalable long-term memory in AI agents, which could be adapted or augmented to support this emotional dimension.
*   **Chapter Summary Compression:** Periodically (e.g., every M scenes or at chapter breaks), the Narrator can assist in auto-writing a summary of the concluded segment. Old, detailed logs (individual memories) can then be pruned or archived once they are encapsulated in these summaries, which themselves become part of the LTM (potentially with an averaged or dominant mood of the summarized period).

For MVP, complex LTM with full Emotional RAG might be simplified, relying on large context windows and basic recency/semantic retrieval for shorter stories. However, the `MemoryManager` architecture and memory storage format should be designed with these advanced LTM features in mind for future integration.

**World State:** Maintain a global `world_state` object that includes:
- Static context: e.g., the overall setting, perhaps a world timeline or any "global" facts.
- Dynamic state: positions of characters, status of important variables (health, inventory, relationships), and any pending events.
- Scene data: which scene/chapter we are in, whose POV it is, etc.
This state can be updated by the world agent or by explicit code after each turn. For instance, if the narrator describes time passing to evening, update world_state["time"] = "evening". If a new character is introduced, add them to the state.

**Consistency Checks:** Optionally, add simple checks when updating state. If a character "dies" in the story, mark them inactive so their agent doesn't act further. If the group moves to a new location, clear or update location-based context.

**Persistence:** If the story is long or if you want to pause/resume, you could serialize the memory and state to disk (e.g., save to JSON after each scene). For real-time prototyping this might not be needed, but it's a consideration when scaling up.

By structuring memory and state separately from the narrative text, we keep a clear record of factual information that the LLM can rely on, rather than re-parsing the entire narrative each time. This separation of "story world model" and "story prose" is important as the project grows.

## Extending to Longer Stories (e.g. Anxiety Is the Dizziness of Freedom)

To scale this prototype to handle longer and more complex stories (like the novella "Anxiety Is the Dizziness of Freedom" with its intricate branching scenarios), consider the following enhancements:

**Chapter or Episode Structure:** Organize the story into chapters or episodes. Each chapter can focus on a subset of the story (a particular subplot or time period). Before a new chapter, summarize the previous one (perhaps with the narrator or a recap function) and use that summary to prime the next chapter's context. This helps keep the context window manageable and the narrative coherent over long spans.

**High-Level Plot Guidance:** Introduce a "director" or outline that guides the major plot points. For example, predefine a sequence of major events or turning points (this can be loosely based on a story you want to emulate or a theme). The world agent can then be guided to inject those events at the right time. In a complex story like Anxiety...Freedom, there are key conceptual events (e.g., using a device that creates parallel realities). You might script those key events into the world agent's behavior so that the simulation eventually encounters them. This ensures the narrative has a direction and doesn't meander endlessly.

**Script/Outline Mode with Beats:** To provide more structured narrative direction, especially for longer stories or when adapting existing plots, a "script mode" will be supported. In this mode, the `WorldAgent` (and potentially Character Agents) can be guided by a sequence of "beats" defined in a preset JSON file. These beats will break down scenes or chapters into smaller, actionable narrative units, outlining key events, character actions, dialogue cues, or emotional shifts. The structure and philosophy behind these beats will draw inspiration from established storytelling concepts, such as those detailed by NovelCrafter for AI-assisted writing ([https://docs.novelcrafter.com/en/articles/8675715-crafting-beats](https://docs.novelcrafter.com/en/articles/8675715-crafting-beats)). This allows for a blend of authored guidance and agent-driven emergence within the framework of the beats.

**Advanced Memory Management:** For a very long story, integrate long-term memory storage. You could use a vector database to store all past events with embeddings, allowing retrieval of relevant past facts on the fly. This prevents the LLM from forgetting important details introduced early on. Both CAMEL and AutoGen support plugging in external memory or retrievers for this purpose (CAMEL integrates with vector stores for long-term memory. In a custom setup, you can manually implement a retrieval step before agent prompts (e.g., find any past event involving the same NPC when that NPC reappears).

**Agent Evolution:** Over a long story, agents might evolve (goals achieved, moods changed, even personalities shifted due to events). Plan to update agent attributes as the story progresses. For example, if a character overcomes a fear, their persona or mood baseline might change (they become more confident). This can be done by modifying the agent's prompt attributes or swapping out their persona description mid-story.

**Scaling Agents:** More characters can be added as needed (perhaps the story introduces new side characters). The framework is already there – you can spin up a new CharacterAgent with its persona and let it participate in turns when present. For extremely large casts, you'd likely only keep active agents in the loop (others can be dormant in memory until they enter the scene).

**Quality and Coherence:** As stories get longer, ensuring coherence is challenging. You might incorporate a critic or editor agent (another possible role) that reads the narrator's output and checks for consistency or quality, then suggests adjustments. This is more advanced, but frameworks like CAMEL consider critic agents for reflection. In a custom setup, you could periodically ask the LLM (or another model) questions about the story so far to catch contradictions.

**Testing with the Example:** Using "Anxiety Is the Dizziness of Freedom" as inspiration, you could test if your system can handle complex concepts like parallel timelines. This might involve the world agent simulating multiple versions of events or a forking narrative. Extending the prototype, you could create multiple world states and sets of agents (one per timeline) and a higher-level narrator weaving between them. That's an ambitious extension, but it shows the importance of an extensible architecture.

In summary, to go from a short story to a novella-length narrative, focus on modularity and state management. The prototype we outlined is modular by design (separate agent logic, world logic, narration). This makes it easier to plug in enhancements like better memory stores, more agents, or outline-driven events. As you scale up, you could gradually incorporate CAMEL or AutoGen components – for example, use CAMEL's memory system or AutoGen's conversation manager – when they add value.

## Conclusion and Next Steps

We have outlined a minimal yet complete design for a multi-agent storytelling system. The custom lightweight architecture is recommended initially for its clarity and control, aligning with the goal of quickly building a working prototype. This design uses four character agents with well-defined personas, goals, **dynamic emotional states, and a two-step private reflection and public planning process.** A world agent enriches the environment, and a narrator module crafts the final prose. It leverages DeepSeek R1 via OpenRouter as the LLM backbone, abstracted so that any model can be used with a flip of a switch. Key implementation details include organizing the code into logical modules (agents, prompts, main loop), defining each agent's persona/memory/goals (drawing on ideas from frameworks like CAMEL for identity and memory, and incorporating Emotional RAG concepts for memory retrieval), and orchestrating turn-by-turn interactions that are then narrated in a show-don't-tell style. We discussed prompt engineering techniques to guide character outputs (including private reflections and public plans) and the narrator's writing to be vivid and immersive. Memory and world state are managed in simple data structures for the MVP, which suffices for short stories and sets the stage for more advanced memory techniques (like those inspired by Mem0 with emotional context) and structured outline-following (using beats) as the project grows.

Next Steps: Begin implementing this step by step. Start by writing the character and world agent classes with stubbed `reflect()`, `plan()`, and `apply_plan()` methods, and a simple main loop. Test it with a very simple scenario and use the narrator to get a feel for the output. Expect to iterate on prompts frequently, especially for the `reflect` and `plan` stages. Once the basic loop works with DeepSeek R1, experiment with swapping in another model (to validate the abstraction). From there, you can build out more complex features (Emotional RAG-based long-term memory, more intricate events) and consider integrating parts of CAMEL or AutoGen for scalability. For project organization, as features like a debug server or UI (as tentatively noted in `systemPatterns.md` with `server.py`) evolve, consideration should be given to placing them in a dedicated `app/` directory. For evaluation, future iterations could include basic statistics such as character participation rates per scene and high-level tracking of character arc progression, perhaps even attempting to quantify emotional trajectory coherence. Overall, this design should let you demonstrate emergent story generation from multi-agent interaction quickly, and provides a path to scaling up to longer, more complex stories as envisioned.