from .llm_interface import LLMInterface
from .ficworld_config import DEFAULT_NARRATOR_LITERARY_TONE, DEFAULT_NARRATOR_TENSE_INSTRUCTIONS
# Potentially import data classes for scene_log items and pov_character_info if defined elsewhere
# from .models import LogEntry, CharacterPublicInfo # Example

class Narrator:
    """
    The Narrator module converts simulation logs into engaging narrative prose,
    adhering to specified stylistic guidelines (e.g., POV, tense, show-don't-tell).
    """
    def __init__(self, llm_interface: LLMInterface):
        """
        Initializes the Narrator with an LLM interface.

        Args:
            llm_interface: An instance of LLMInterface to communicate with the language model.
        """
        self.llm_interface = llm_interface

    def render(self, scene_log: list, pov_character_name: str, pov_character_info: dict) -> str:
        """Renders a scene's log into narrative prose from a specific character's POV.

        Args:
            scene_log: A list of factual outcomes from the scene.
                       Each item could be a dict like:
                       {"actor": "Name", "outcome": "Description of what happened", "mood_during_action": {...}}
            pov_character_name: The name of the character from whose perspective the scene is narrated.
            pov_character_info: A dictionary containing persona, goals, and mood of the POV character.
                                e.g., {"persona": "Summary of persona", "goals": ["Goal 1", "Goal 2"], "mood": {"joy": 0.1, ...}}

        Returns:
            A string containing the narrative prose for the scene.
        """
        # Use configurable stylistic choices
        tense_instructions = DEFAULT_NARRATOR_TENSE_INSTRUCTIONS
        pov_instructions = f"third-person limited perspective, focusing on {pov_character_name}"
        desired_literary_tone = DEFAULT_NARRATOR_LITERARY_TONE

        system_prompt = f"""
        You are a masterful storyteller and narrator for FicWorld. Your task is to transform a log of events and actions into engaging narrative prose.

        **Style Guidelines:**
        - Write in {tense_instructions}.
        - Use {pov_instructions}.
        - Strictly adhere to the "show, don't tell" principle. Describe emotions and thoughts through actions, dialogue delivery, and sensory details rather than stating them directly.
        - Weave in environmental details and character reactions naturally.
        - The desired literary tone is: {desired_literary_tone}.
        - Do NOT simply list events or repeat dialogue verbatim from the log. Narrate them vividly.
        - Do NOT speak as an AI, break the fourth wall, or add meta-commentary. Write it like a passage from a novel.
        """

        # Format pov_character_info for the prompt
        pov_persona = pov_character_info.get("persona", "No persona summary available.")
        goals_list = pov_character_info.get("goals", ["No specific goals available."])
        pov_goals = "\n".join([f"- {goal}" for goal in goals_list])
        pov_mood = str(pov_character_info.get("mood", "No mood data available.")) # Convert dict to string for simple display

        # Format scene_log for the prompt
        formatted_scene_log_lines = []
        if not scene_log:
            formatted_scene_log_lines.append("No specific events occurred in this scene.")
        else:
            for entry in scene_log:
                actor = entry.get("actor", "Unknown")
                outcome = entry.get("outcome", "No specific outcome.")
                mood_during_action = entry.get("mood_during_action", None) # Optional
                
                log_line = f"[{actor}]: {outcome}"
                if mood_during_action:
                    log_line += f" (Mood during action: {mood_during_action})"
                formatted_scene_log_lines.append(log_line)
        formatted_scene_log = "\n".join(formatted_scene_log_lines)
        
        user_prompt = f"""
        Narrate the following scene.

        **Point-of-View Character for this scene:** {pov_character_name}
        **POV Character Information:**
          - Persona Summary: {pov_persona}
          - Current Goals:
{pov_goals}
          - Current Mood: {pov_mood}

        **Scene Log (Factual Outcomes):**
{formatted_scene_log.strip()}

        Rewrite this log as a coherent and engaging prose passage, strictly adhering to the established narrative style and focusing on {pov_character_name}'s limited perspective. Draw upon their persona and mood to enrich the descriptions of their actions, perceptions, and internal reactions (implied, not stated).
        """

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ]

        try:
            # Use the synchronous version of the LLM call
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt.strip(), 
                user_prompt=user_prompt.strip()
            )
            
            # Attempt to extract text from the response
            # This might need adjustment based on the actual structure of LLMInterface.generate_response() output
            if isinstance(response, str):
                return response
            elif hasattr(response, 'text') and isinstance(response.text, str):
                return response.text
            elif isinstance(response, dict) and 'text' in response and isinstance(response['text'], str):
                return response['text']
            else:
                # If the response is not a string or a known object with a text attribute/key, log and return error
                print(f"Warning: Narrator received an unexpected response format: {type(response)}. Content: {str(response)[:200]}...")
                return "Error: Could not generate narration due to unexpected LLM response format."

        except Exception as e:
            # Log the error appropriately in a real application
            print(f"Error during Narrator LLM call: {e}")
            return f"Error: Could not generate narration. Details: {e}" 