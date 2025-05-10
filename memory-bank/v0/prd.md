# AgentVerse: An Autonomous Story Generator

Goal: To create coherent short stories and whole books through autonomous multi-agent coordination. **Each character is an autonomous agent** with its own persona, memories, motivations, and behaviors. Rather than a single omniscient narrator, the narrative emerges from the **interactions among these character agents** within a shared world. A separate *world-building agent* (or “world agent”) sets the scene and enforces global consistency (the environment, events, and overall plot constraints), but direct control over the story is minimized. This approach lets characters “take on a life of their own,” aligning with the idea that once characters and worlds are established, stories should unfold from their dynamics.

MVP goal:
Build a system that can generate coherent short stories → full novels through emergent interaction of autonomous character agents. We take BookWorld’s proven design (role agents + world agent + narrator) and adapt it for a lean, easily-swappable Python stack running on OpenRouter models (default: DeepSeek R1).

## Tech Stack

Python
OpenRouter - default to Deepseek R1, but should be easy to swap to any LLM model like Gemini 2.5 Pro

We will start with a simple custom architecture for quick prototyping and clarity. This lets us define the storytelling loop and prompt patterns explicitly. We should still draw inspiration from CAMEL’s design (roles, memory, etc.) and even integrate CAMEL later for scaling. CAMEL would be the next choice if we want a framework – it’s tailored for agent societies and is compatible with OpenRouter out-of-the-box.

We should design this project in a way that it is easy to swap to using another framework like CAMEL. CAMEL's pros include:
- High-level abstractions like AgentSociety for defining agent roles and interactions, built-in memory management, and easy model integration (including DeepSeek via OpenRouter)
- Cons – Current high-level APIs (e.g. RolePlaying) are mainly for two-agent role-play; using it for four characters plus a world agent may require custom orchestration or using lower-level society tools.

Refer to the directory `bookworld-original` to see an implementation we can use as reference.

## System Architecture Overview

Read [systemPatterns](./systemPatterns.md) for detail.

The system will consist of several components orchestrating a multi-agent story simulation:

**Character Agents (4)** – Autonomous characters each with a distinct persona, goals, and mood. They “live” in the story world and decide actions or dialogue in each turn based on their personality and objectives.

**World Agent (1)** – An agent representing the environment and plot events. It sets the scene, enforces world rules, and occasionally injects new events or challenges that drive the narrative forward.

**Narrator Module** – Not exactly a character in the story, but a module (using the LLM) that observes the raw interactions (dialogue/actions from character and world agents) and rewrites them into narrative prose. The narrator produces the story text in a show-don’t-tell, limited POV style, making it engaging and coherent for the reader.

**LLM Interface** – An abstraction layer to call the language model (DeepSeek R1 via OpenRouter) for any agent that needs to generate text. This ensures model calls are handled uniformly and makes it easy to swap the LLM (e.g., switching to GPT-4 or another model by changing one config).

**Memory & World State** – A storage mechanism to keep track of what has happened (agent memories) and the current state of the world (locations, objects, time, etc.). This ensures consistency as the story progresses, especially as context length grows.

All these components interact during simulation rounds. The world agent provides context, character agents act and react, and the narrator turns those actions into the story narrative. The LLM (DeepSeek R1) is the engine behind each agent’s decision and the narrator’s prose, guided by prompts that shape its outputs.


## Character Agents: Persona, Goals, Memory, Mood

Each character agent can be represented as a Python class (or a config + functions) encapsulating its identity and state:

**Persona/Role:** A description of who the character is – their backstory, personality, and demeanor. This will be baked into the agent’s system prompt or initial instructions. For example, a knight character’s persona might include bravery, loyalty, and old-fashioned speech patterns. The persona effectively acts as the agent’s “role” definition

**Goals:** Each character has one or more objectives or motivations driving them. Goals can be long-term (“protect the kingdom”) and short-term (“find shelter for the night”). These will influence how the agent responds each turn. We can include the goals in the prompt (e.g., reminding the agent “Your goal is to reunite with your lost sister”).

**Mood/Emotion:** The agent’s current emotional state (e.g., anxious, confident, suspicious). Mood can change based on story events. It can modulate the agent’s tone or decisions. For instance, a frightened mood might make the agent speak in short, nervous sentences. Mood can be stored as a simple attribute and updated when the world agent triggers something (like a scary event might set all characters’ mood to “fearful”).

**Memory:** The agent’s memory consists of knowledge of past events, observations, and interactions. This can be implemented minimally as a list of recent important moments or dialogue lines that the agent has “seen.” For now, memory might just be the recent dialogue turns involving that agent (to maintain context within the LLM prompt). In a more advanced version, this could tie into a vector database or a longer-term memory store, but initially a Python list of strings per agent (truncated to fit the context window) works. CAMEL-like designs emphasize memory so agents can reference past interactions and we’ll do the same.

**Defining the Agent:** In code, a CharacterAgent class might have attributes for persona, goals, mood, and memory. It would also have an `act(world_state, observations)` method. This act method constructs a prompt combining:
- The agent’s persona and goals (as a system or context message).
- A summary of relevant world state and recent events (from the world agent or global log) that the agent is aware of.
- Possibly the agent’s own last action or internal thought (from memory).
- An instruction to respond in character, deciding on an action or dialogue.

When act() is called, it sends this prompt to the LLM (DeepSeek R1 via our interface) and returns the LLM’s output as the agent’s action/dialogue for that turn. Each character agent operates similarly, ensuring they behave according to their personality and objectives.

### World Agent: Environment and Event Simulation

The world agent is responsible for the dynamic environment of the story. It can be implemented as a special agent or just a set of functions that update the scene:

**Setting the Scene:** At the start of the story or each scene, the world agent provides a description of the environment. For example, it might describe the location (“a dark forest on a stormy night”), time of day, and any background events (“wolves howl in the distance”). This context is fed into the prompts for character agents so they know what’s happening around them.

**Injecting Events:** The world agent can occasionally introduce new events or challenges. For instance, it might announce “suddenly, a stranger appears on the road” or “the ground trembles from a minor earthquake.” These events will affect characters’ decisions and moods. The injection can be done every few turns or when a certain condition is met (perhaps randomly or according to a simple plot script).

**World State Tracking:** It maintains a state representation of the world – locations of characters, inventory of important objects, time progression, etc. This state can be a simple dictionary or custom class (e.g., world_state = { "location": "forest", "weather": "rainstorm", "nearby_creatures": ["wolves"] }). After each turn, the world state might be updated (if a character starts a fire, weather might change to clear if the fire magically stops the rain, etc.).

**Consistency and Rules:** The world agent can enforce simple physics or story logic. For example, if a character tries to do something impossible (like see in complete darkness without a light), the world agent’s next update can correct or highlight that (“it’s too dark to see clearly”). This keeps the narrative coherent.

In practice, the world agent could be an LLM as well: given the current state, it could generate a descriptive update each round (“The rain intensifies, and lightning strikes a nearby tree.”). However, to start minimally, you might script the world events or use random draws for events. If using the LLM for this, you’d give it a prompt like “You are the world and narrative engine. Describe any new events happening in the environment given the current state and recent actions, in a neutral factual way.” The world agent’s outputs become part of the context for the next round.

## Narrator Module: Narrative Rendering

The narrator module takes the raw simulation outputs (the dialogue/actions from the character agents and the world agent’s descriptions) and rewrites them into a polished story form. This is where we enforce the “show, don’t tell” and limited POV style:

**Show, Don’t Tell:** The narrator should convert factual or blunt statements into vivid descriptions. For example, if a character agent output was: Alice (agent): "I feel scared of the dark forest.", the narrator might rewrite this as prose: Alice’s heart hammered in her chest as she peered into the pitch-black forest, fingers trembling on the hilt of her sword. This conveys the fear through description and action rather than explicitly saying “she is scared.”

**Limited POV:** We choose a perspective (usually one character per scene) and have the narrator describe events only through what that character could perceive. If the POV is Alice’s, the narrator will detail Alice’s thoughts, feelings, and sensory impressions, but won’t mention another character’s hidden thoughts. This makes the story feel grounded and personal. We can decide the POV character for each scene (perhaps rotate among the protagonists or stick to one main hero).

**Narration Process:** After each simulation round or scene, we gather the sequence of events: e.g., World described X, Character A said Y, Character B did Z, etc. We then feed this into the narrator prompt. The prompt would be something like: a system message with guidelines (“You are a narrator writing a story. Use past tense, third-person limited to Alice’s perspective (for example), and a descriptive ‘show, don’t tell’ style. Do not simply repeat the dialogue; instead narrate it vividly.”). Then the conversation history message might list the raw events (possibly labeled or in quotes). The narrator (as the LLM) then produces a narrative paragraph or two that retells those events in flowing story prose.

**Incremental Story Output:** The narrator’s output can be appended to a growing story text. After each scene, we accumulate the narrator’s paragraphs. This is what a reader would see as the story. The intermediate agent dialogue or world state dumps would not be shown to the end user, only the narrator’s crafted narrative.

By separating narrator duties, we ensure the final story is cohesive and stylistically consistent, rather than a disjointed chat log. Prompt engineering is key here – the narrator’s system prompt should include style instructions (e.g., focus on sensory details, emotions through actions, maintain the character’s voice in dialogue, etc.). You might also give the narrator examples of the desired style if needed (few-shot examples of “tell vs show” rewrites).

**LLM Integration and Model Abstraction**

We will use DeepSeek R1 via OpenRouter as the language model for all agents initially. To keep the design flexible, it’s wise to create an abstraction layer for model calls:

OpenRouter API: OpenRouter allows access to various models (including DeepSeek R1) through an OpenAI-compatible API endpoint. We can use an OpenAI Python client (by pointing it to OpenRouter’s URL and API key) or just do requests calls. This means our code can call openai.ChatCompletion.create(...) with the appropriate model name (e.g., deepseek/deepseek-r1:free) and API key, and OpenRouter will handle it. By isolating this in a module (say models.py or a helper function), we can easily swap the model name or endpoint.

Model Abstraction: Define a function like generate_response(prompt_messages, model="deepseek-r1") that wraps the API call. All agents and the narrator will use this function. It takes a list of messages (in OpenAI format: system + conversation messages) and returns the LLM’s reply. Internally, this could be implemented with OpenAI’s SDK or HTTP calls to OpenRouter.

Swapping Models: Because we use a generic interface, switching to another model (GPT-4, Anthropic Claude, etc.) later is simple – just change the model name or route in one place. The prompts and logic remain the same. This fulfills the “clean abstraction to allow easy swapping of models” requirement.

Libraries Needed: If using OpenRouter via OpenAI API compatibility, the openai Python package can be used (set openai.api_base to https://openrouter.ai/api/v1 and supply the key). Alternatively, use requests to POST to OpenRouter’s endpoints. In addition, we will likely use standard packages like dataclasses (to define agent data structures) and perhaps typer or argparse if we want a CLI for the script. For now, focus on core functionality: ensure the OpenRouter call works with the provided model.

By handling all LLM interactions in one place, we also make it easier to add features like logging or cost tracking for the API calls, or caching responses during development.

### Simulation Orchestration: Turns and Scenes

The orchestration logic controls how agents interact turn by turn, and how the story transitions between scenes:

**Initialization:** The world agent sets up the initial scene (environment description, initial world state). Each character agent is initialized with their persona, goals, starting mood, and any prior knowledge (which may be none for a fresh story).

**Turn Loop:** In each turn, agents take actions one after another, influenced by what happened earlier in the turn:

1. World Context Update: (Optional each turn) The world agent may provide an update or minor event at the start of the turn (e.g., “the wind picks up.”). This ensures the environment remains dynamic even if no big event occurs.

2. Character Actions: Each character agent gets a chance to act or speak. We decide an order – possibly fixed (Agent1 through Agent4 each turn) or context-driven (maybe agents closest to an event react first). In each sub-turn:
    - Gather context: the world state, last narrator output or last raw actions, plus the agent’s memory.
    - Call the agent’s act() (LLM prompt) to decide what the agent does now. For example, Agent1 might decide to say “We should find shelter,” Agent2 might then react “I know a cave nearby,” etc.
    - Update the global log or state with the agent’s action. Also update that agent’s memory (they “remember” what they just did or said).

3. World Agent Events: After characters act, the world agent might react to their actions. For example, if a character attempted something, the world agent determines the outcome: “the door is locked, their attempt to open it fails.” This can be done every turn or only when needed (if character actions directly warrant a world response).

4. Narration: Once a round of all agents acting is complete, we have a collection of interactions for that time step. Now the narrator module is invoked to turn these into a narrative passage. The input to the narrator is essentially the transcript of what happened (including any important internal thoughts if you choose to expose them, though probably just actions and dialogue). The narrator produces a prose description covering the whole turn from the chosen POV.

5. Story Accumulation: Append the narrator’s output to the story text. Also, the narrator’s output can be fed back into the agents’ memories as a summarized “this is what just happened” (so they have a consistent view of the recent narrative).

**Scene Transitions:** A scene might consist of several turns. We define a condition for transitioning to a new scene or chapter. For example, after ~5 turns, or after a major event (world agent triggers an event “End of Chapter 1: the party escapes the forest”), we conclude the scene. At a scene break, we might change the POV character for narration, or relocate the characters (update world state significantly, like moving to a town). Scene transitions can also help manage the context length – at a break, we might summarize or trim old memory.

**Stopping Criteria:** The simulation could run for a fixed number of scenes or until a certain goal is achieved (maybe one of the character’s main goals is reached, or a natural story climax occurs). Also, incorporate a safety break: if the story starts looping or the LLM outputs go off track, the loop can terminate after a max number of turns with a warning.

This orchestrated cycle ensures that each agent contributes to the evolving storyline and that their interactions are turned into a coherent narrative at regular intervals. You could implement this loop in main.py as straightforward for loops and function calls. Using an event loop or more complex scheduler isn’t necessary for a simple prototype.

## Prompt Engineering Patterns

Crafting effective prompts is crucial to make sure agents behave believably and the narrator writes in the desired style:

**Character Agent Prompts:** Each character’s prompt will likely use a combination of a system message and a few-shot or informative context. For example:
System message for agent: “You are [Character Name], a fictional character in a story. Persona: [brief description of personality and background]. Goals: [list of goals]. Mood: [current mood]. You will decide your next action or dialogue in the story, staying in character and focusing on your goals.”
**Context message(s):** Include the relevant world description (“The scene: [environment detail]”), and perhaps the last few actions from other characters (“Earlier this turn: [Other Character] said/did XYZ.”). This gives situational awareness.
**User message (prompt):** A direct instruction or question to prompt action, e.g., “What do you do or say next?” or “Decide your next action in one or two sentences.”

This structure guides the LLM to produce an output as the character. We might also append guidelines like “Speak in first person if it’s dialogue, or describe your action in third person.” This way, the output could be like: "Alice says, 'Let's stick together.'" or "Alice cautiously steps forward, eyes scanning the darkness." – depending on if we want direct speech or description. For ease of parsing, you can ask the agent to include their name or speak in dialogue form. The narrator later will turn any quoted speech into narrative form.

**World Agent Prompt:** The world agent can have a system prompt: “You are the world and setting of the story. You describe environment changes and outcomes of actions.” Provide the current state as context. Then a prompt like: “Given the recent actions, describe any immediate outcome or new event.” This encourages the LLM to output a neutral description (which might be used as is, or just for narrator reference).

**Narrator Prompt:** The narrator’s prompt is the most creative. A possible structure:
**System message:** “You are a storyteller narrating a fiction scene. Write in past tense, third person limited perspective (focused on [Character]'s POV). Use a 'show, don’t tell' style with vivid sensory details and emotions implied through actions and dialogue. Do not enumerate events or speak as an AI; write it like a novel.”
**User message:** Provide the raw log of the scene, e.g., a bullet list or script:
[World] The forest is dark and quiet.
[Alice] says "We should find shelter."
[Bob] lights a torch.
... etc.
Then: “Narrate this scene in a coherent paragraph:”

With this, the LLM should transform the script into flowing prose. We might include an example in the prompt (few-shot) of a tiny script and a narrated version, to reinforce the style.

Few-shot Examples: Provide one or two examples of converting telling to showing could help.

Token Limits: Keep prompts concise to avoid hitting context limits. Use summaries for older events. For example, an agent’s persona can be a short paragraph, not pages of backstory, otherwise the prompt becomes too large. Similarly, pass only relevant recent events to each agent. However, if we use Gemini 2.5 Pro we will have a large context window.

Iterative Refinement: You might need to tweak these prompts after testing. If a character starts going out of character or the narrator writes in an expository way, refine the instructions. Prompt engineering is an iterative process – start simple, then add constraints or examples as needed.

By establishing these patterns, we ensure each agent and the narrator LLM knows its role and style. This approach mirrors how multi-agent frameworks structure roles (e.g., CAMEL’s role definitions for identity and behavior) but here we manually design the prompts for our story needs.

## Memory and World State Management

Even a short story can produce a lot of information. We need to manage what each agent “remembers” and how the world state is updated:

**Agent Memory:** For the prototype, use a simple strategy like recency memory: each agent keeps the last N interactions or observations relevant to them. This could be stored as a list of text snippets. Before an agent acts, you include these in its prompt (perhaps summarized if long). For example, Alice’s memory might contain “You remember Bob was injured earlier” so she can act concerned. We can manually curate memory: after each narrator output, tag key points for each character (like update Alice’s memory with “Bob is limping”). In code, CharacterAgent might have self.memory and methods remember(event) and recall() to produce a memory summary for prompts.
- N can be very large, assuming Gemini's 2.5 Pro context window

**Long-Term Memory Extension:** To support longer narratives, we can integrate a vector store or database. Frameworks like CAMEL allow memory modules (short-term vs long-term). In a custom solution, you could use something like FAISS or an embedding-based retrieval: store past events as embeddings, and retrieve the most relevant ones each turn (e.g., if a past NPC was mentioned and comes back later, retrieve that memory). For now, this is optional – a simple list and some manual summarizing works for short stories.
- For MVP, we can avoid even summarizing, just send EVERYTHING to the model. Later on we can do vector databases or something like mem0.

**World State:** Maintain a global `world_state` object that includes:
- Static context: e.g., the overall setting, perhaps a world timeline or any “global” facts.
- Dynamic state: positions of characters, status of important variables (health, inventory, relationships), and any pending events.
- Scene data: which scene/chapter we are in, whose POV it is, etc.
This state can be updated by the world agent or by explicit code after each turn. For instance, if the narrator describes time passing to evening, update world_state["time"] = "evening". If a new character is introduced, add them to the state.

**Consistency Checks:** Optionally, add simple checks when updating state. If a character “dies” in the story, mark them inactive so their agent doesn’t act further. If the group moves to a new location, clear or update location-based context.

**Persistence:** If the story is long or if you want to pause/resume, you could serialize the memory and state to disk (e.g., save to JSON after each scene). For real-time prototyping this might not be needed, but it’s a consideration when scaling up.

By structuring memory and state separately from the narrative text, we keep a clear record of factual information that the LLM can rely on, rather than re-parsing the entire narrative each time. This separation of “story world model” and “story prose” is important as the project grows.

## Extending to Longer Stories (e.g. Anxiety Is the Dizziness of Freedom)

To scale this prototype to handle longer and more complex stories (like the novella “Anxiety Is the Dizziness of Freedom” with its intricate branching scenarios), consider the following enhancements:

**Chapter or Episode Structure:** Organize the story into chapters or episodes. Each chapter can focus on a subset of the story (a particular subplot or time period). Before a new chapter, summarize the previous one (perhaps with the narrator or a recap function) and use that summary to prime the next chapter’s context. This helps keep the context window manageable and the narrative coherent over long spans.

**High-Level Plot Guidance:** Introduce a “director” or outline that guides the major plot points. For example, predefine a sequence of major events or turning points (this can be loosely based on a story you want to emulate or a theme). The world agent can then be guided to inject those events at the right time. In a complex story like Anxiety…Freedom, there are key conceptual events (e.g., using a device that creates parallel realities). You might script those key events into the world agent’s behavior so that the simulation eventually encounters them. This ensures the narrative has a direction and doesn’t meander endlessly.

**Advanced Memory Management:** For a very long story, integrate long-term memory storage. You could use a vector database to store all past events with embeddings, allowing retrieval of relevant past facts on the fly. This prevents the LLM from forgetting important details introduced early on. Both CAMEL and AutoGen support plugging in external memory or retrievers for this purpose (CAMEL integrates with vector stores for long-term memory. In a custom setup, you can manually implement a retrieval step before agent prompts (e.g., find any past event involving the same NPC when that NPC reappears).

**Agent Evolution:** Over a long story, agents might evolve (goals achieved, moods changed, even personalities shifted due to events). Plan to update agent attributes as the story progresses. For example, if a character overcomes a fear, their persona or mood baseline might change (they become more confident). This can be done by modifying the agent’s prompt attributes or swapping out their persona description mid-story.

**Scaling Agents:** More characters can be added as needed (perhaps the story introduces new side characters). The framework is already there – you can spin up a new CharacterAgent with its persona and let it participate in turns when present. For extremely large casts, you’d likely only keep active agents in the loop (others can be dormant in memory until they enter the scene).

**Quality and Coherence:** As stories get longer, ensuring coherence is challenging. You might incorporate a critic or editor agent (another possible role) that reads the narrator’s output and checks for consistency or quality, then suggests adjustments. This is more advanced, but frameworks like CAMEL consider critic agents for reflection. In a custom setup, you could periodically ask the LLM (or another model) questions about the story so far to catch contradictions.

**Testing with the Example:** Using “Anxiety Is the Dizziness of Freedom” as inspiration, you could test if your system can handle complex concepts like parallel timelines. This might involve the world agent simulating multiple versions of events or a forking narrative. Extending the prototype, you could create multiple world states and sets of agents (one per timeline) and a higher-level narrator weaving between them. That’s an ambitious extension, but it shows the importance of an extensible architecture.

In summary, to go from a short story to a novella-length narrative, focus on modularity and state management. The prototype we outlined is modular by design (separate agent logic, world logic, narration). This makes it easier to plug in enhancements like better memory stores, more agents, or outline-driven events. As you scale up, you could gradually incorporate CAMEL or AutoGen components – for example, use CAMEL’s memory system or AutoGen’s conversation manager – when they add value.

## Conclusion and Next Steps
We have outlined a minimal yet complete design for a multi-agent storytelling system. The custom lightweight architecture is recommended initially for its clarity and control, aligning with the goal of quickly building a working prototype. This design uses four character agents with well-defined personas and goals, a world agent to enrich the environment, and a narrator module to craft the final prose. It leverages DeepSeek R1 via OpenRouter as the LLM backbone, abstracted so that any model can be used with a flip of a switch. Key implementation details include organizing the code into logical modules (agents, prompts, main loop), defining each agent’s persona/memory/goals (drawing on ideas from frameworks like CAMEL for identity and memory), and orchestrating turn-by-turn interactions that are then narrated in a show-don’t-tell style. We discussed prompt engineering techniques to keep character outputs in character and the narrator’s writing vivid and immersive. Memory and world state are managed in simple data structures, which suffices for short stories and sets the stage for more advanced memory techniques as the project grows.

Next Steps: Begin implementing this step by step. Start by writing the character and world agent classes with stubbed act() methods, and a simple main loop. Test it with a very simple scenario and use the narrator to get a feel for the output. Expect to iterate on prompts frequently. Once the basic loop works with DeepSeek R1, experiment with swapping in another model (to validate the abstraction). From there, you can build out more complex features (long-term memory, more intricate events) and consider integrating parts of CAMEL or AutoGen for scalability. Overall, this design should let you demonstrate emergent story generation from multi-agent interaction quickly, and provides a path to scaling up to longer, more complex stories as envisioned.