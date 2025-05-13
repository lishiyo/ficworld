#!/usr/bin/env python
"""
FicWorld - Multi-agent storytelling system

This is the main entry point for running FicWorld simulations.
"""
import argparse
import json
import os
import sys
from pathlib import Path
import dataclasses # Added for asdict

from modules.config_loader import ConfigLoader
from modules.llm_interface import LLMInterface
from modules.memory_manager import MemoryManager
from modules.character_agent import CharacterAgent
from modules.world_agent import WorldAgent
from modules.narrator import Narrator
from modules.relationship_manager import RelationshipManager
from modules.models import CharacterState # Assuming CharacterState is needed by WorldAgent or for init
import logging # For debug logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='FicWorld - Multi-agent storytelling system')
    parser.add_argument('--preset', type=str, required=True, help='Name of the preset to use (e.g., demo_forest_run)')
    parser.add_argument('--output-dir', type=str, help='Directory to save output (default: outputs/<preset_name>)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose logging')
    return parser.parse_args()


def setup_output_directory(preset_name, custom_output_dir=None):
    """Set up the output directory for this run."""
    output_dir = Path(custom_output_dir) if custom_output_dir else Path('outputs') / preset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main():
    """Main entry point for FicWorld."""
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        logger.info(f"Loading preset: {args.preset}")
        config = config_loader.load_full_preset(args.preset)
        
        # Set up output directory
        output_dir = setup_output_directory(args.preset, args.output_dir)
        logger.info(f"Output will be saved to: {output_dir}")
        
        # Save configuration for reference
        with open(output_dir / 'config_used.json', 'w', encoding='utf-8') as f:
            json.dump({
                "preset_name": args.preset,
                "world_name": config["world"].world_name,
                "roles": [role.archetype_name for role in config["roles"]],
                "mode": config["preset"].mode,
                "max_scenes": config["preset"].max_scenes,
                "llm": dataclasses.asdict(config["preset"].llm) # Changed to use dataclasses.asdict
            }, f, indent=2)
        
        # Display loaded configuration
        logger.info("\nLoaded Configuration:")
        logger.info(f"World: {config['world'].world_name}")
        logger.info(f"Roles: {', '.join(role.archetype_name for role in config['roles'])}")
        logger.info(f"Simulation Mode: {config['preset'].mode}")
        logger.info(f"Max Scenes: {config['preset'].max_scenes}")
        logger.info(f"LLM: {config['preset'].llm}")
        
        # Initialize LLM Interface
        logger.info("Initializing LLMInterface...")
        llm_interface = LLMInterface(
            model_name=config["preset"].llm.model_name
        )
        
        # Initialize Memory Manager
        logger.info("Initializing MemoryManager...")
        memory_manager = MemoryManager() # Using default in-memory for now
        
        # Initialize Relationship Manager
        logger.info("Initializing RelationshipManager...")
        relationship_manager = RelationshipManager()
        
        # Initialize Character Agents
        logger.info("Initializing Character Agents...")
        character_agents = {}
        initial_character_states = {}
        for role_archetype in config["roles"]:
            # For MVP, let's assume role_archetype.name_template can be used directly or with a simple replacement
            # If name_template is "Sir {Name}", and we don't have a specific name, we might use the archetype name
            # Or, a more robust way would be to have instantiated character names in the preset.
            # For now, let's use a simplified naming based on archetype_name for the agent key.
            # Actual character names used in simulation should be derived properly if needed.
            char_name = role_archetype.archetype_name # Simplified for agent key
            
            # Create initial character state. This might be more complex depending on WorldAgent needs.
            # For now, a basic CharacterState. Location might come from world_definition or be dynamic.
            initial_state = CharacterState(
                name=char_name, # This should ideally be the character's actual story name
                persona=role_archetype.persona_template, # Or an instantiated persona
                goals=[goal for goal in role_archetype.goal_templates], # Or instantiated goals
                current_mood=role_archetype.to_mood_vector(), # Corrected to use to_mood_vector()
                activity_coefficient=role_archetype.activity_coefficient,
                location="initial_location", # Placeholder, should be set by WorldAgent or config
                conditions=[],
                inventory={}
            )
            initial_character_states[char_name] = initial_state
            
            character_agents[char_name] = CharacterAgent(
                role_archetype=role_archetype,
                llm_interface=llm_interface,
                memory_manager=memory_manager
                # relationship_manager=relationship_manager, # This line should be removed
                # initial_world_state will be passed per turn by WorldAgent/loop
            )
            logger.info(f"Initialized CharacterAgent: {char_name}")

        # Initialize World Agent
        logger.info("Initializing WorldAgent...")
        world_agent = WorldAgent(
            world_definition=config["world"],
            llm_interface=llm_interface, # If WA uses LLM for its decisions
            character_states=initial_character_states, # Corrected parameter name
            relationship_manager=relationship_manager, # Added relationship_manager
            # TODO: Add configurable thresholds for WA from preset if available
            # max_scene_turns=config["preset"].get("max_scene_turns", 20), # Example
            # stagnation_threshold=config["preset"].get("stagnation_threshold", 3), # Example
        )
        
        # Initialize Narrator
        logger.info("Initializing Narrator...")
        narrator = Narrator(
            llm_interface=llm_interface,
            # narrator_tone=config["preset"].get("narrator_tone", "neutral"), # Example
            # narrator_tense=config["preset"].get("narrator_tense", "past") # Example
        )
        
        logger.info("\n--- Starting Simulation ---")
        full_story_prose = []
        full_simulation_log = []

        # Main simulation loop (based on systemPatterns.md and tasks.md)
        for scene_num in range(config["preset"].max_scenes):
            logger.info(f"Starting Scene: {scene_num + 1}")
            world_agent.init_scene() # Resets/prepares world_state for the new scene
            
            # log_for_narrator should store factual outcomes, not full log_entry dicts as per systemPatterns
            # For detailed logging, we'll use full_simulation_log
            current_scene_factual_outcomes = []
            
            turn_num = 0
            # Filter full_simulation_log for current scene to pass to judge_scene_end
            current_scene_log_entries = [entry for entry in full_simulation_log if entry.get("scene") == scene_num + 1]
            while not world_agent.judge_scene_end(current_scene_log_entries):
                turn_num += 1
                logger.info(f"Scene {scene_num + 1}, Turn {turn_num}")

                actor_name, actor_state_ref_from_wa = world_agent.decide_next_actor() # WA returns actor_name and its state
                
                # The world_agent.decide_next_actor() should ideally return the agent object
                # or a name that can be used to look up the agent and its state.
                # For now, assuming actor_name is a key to character_agents and world_agent.world_state.character_states
                if actor_name not in character_agents:
                    logger.error(f"Actor {actor_name} decided by WorldAgent not found in character_agents. Skipping turn.")
                    # Potentially add a counter to break if this happens too often
                    continue
                
                actor_agent = character_agents[actor_name]
                # world_state is managed by WorldAgent. Agents get a view of it.
                current_world_view = world_agent.get_world_state_view_for_actor(actor_name)
                actor_current_mood = world_agent.get_character_mood(actor_name)

                # Get V1 contexts
                logger.debug(f"Fetching relationship context for {actor_name}...")
                relationship_context = relationship_manager.get_context_for(actor_name)
                logger.debug(f"Fetching recent scene summaries...")
                scene_summary_context = memory_manager.get_recent_scene_summaries() # Default count (3)

                # Retrieve relevant memories
                # The query for memory retrieval might need to be more dynamic
                logger.debug(f"Retrieving memories for {actor_name} with mood: {actor_current_mood}")
                relevant_memories = memory_manager.retrieve(
                    actor_name=actor_name,
                    query_text="current situation assessment and reflection", # Generic query
                    current_mood=actor_current_mood
                )
                
                # Actor reflects (private)
                logger.debug(f"Actor {actor_name} reflecting...")
                reflection_output = actor_agent.reflect_sync(
                    world_state=current_world_view, # Changed from world_state_summary
                    relevant_memories=relevant_memories,
                    relationship_context=relationship_context, # Added V1 context
                    scene_summary_context=scene_summary_context # Added V1 context
                )
                # Update mood in WorldAgent's state
                world_agent.update_character_mood(actor_name, reflection_output.updated_mood)
                logger.debug(f"{actor_name} updated mood to: {reflection_output.updated_mood}")
                
                # Actor plans (public)
                logger.debug(f"Actor {actor_name} planning...")
                plan_json = actor_agent.plan_sync(
                    world_state=current_world_view,
                    relevant_memories=relevant_memories,
                    internal_thought_summary=reflection_output.internal_thought,
                    relationship_context=relationship_context, # Added V1 context
                    scene_summary_context=scene_summary_context # Added V1 context
                )
                logger.info(f"Actor {actor_name} planned: {plan_json.action} - {plan_json.details}")
                
                # WorldAgent applies plan and gets factual outcome
                logger.debug(f"WorldAgent applying plan for {actor_name}...")
                factual_outcome = world_agent.apply_plan(
                    actor_name=actor_name,
                    plan_json=plan_json
                )
                logger.info(f"Factual outcome for {actor_name}'s plan: {factual_outcome}")
                
                # Log entry for detailed simulation log
                log_entry = {
                    "scene": scene_num + 1,
                    "turn": turn_num,
                    "actor": actor_name,
                    "plan": dataclasses.asdict(plan_json) if plan_json else None, # Changed to dataclasses.asdict
                    "reflection_internal_thought": reflection_output.internal_thought,
                    "mood_before_plan": dataclasses.asdict(actor_current_mood) if actor_current_mood else None, # Mood before reflection
                    "mood_after_reflection": dataclasses.asdict(reflection_output.updated_mood) if reflection_output.updated_mood else None,
                    "outcome": factual_outcome,
                    "is_world_event": False
                }
                full_simulation_log.append(log_entry)
                current_scene_log_entries.append(log_entry) # Add full entry to pass to judge_scene_end
                current_scene_factual_outcomes.append(f"{actor_name}: {factual_outcome}") 
                
                # Update world state based on outcome
                world_agent.update_from_outcome(factual_outcome)

                # Memory: Actor remembers the outcome
                logger.debug(f"Actor {actor_name} remembering outcome...")
                memory_manager.remember(
                    actor_name=actor_name,
                    event_description=factual_outcome,
                    mood_at_encoding=world_agent.get_character_mood(actor_name) # Mood after action
                )
                
                # World event injection
                if world_agent.should_inject_event():
                    logger.info("WorldAgent injecting event...")
                    event_outcome = world_agent.generate_event()
                    logger.info(f"World event: {event_outcome}")
                    current_scene_factual_outcomes.append(f"World: {event_outcome}")
                    
                    event_log_entry = {
                        "scene": scene_num + 1,
                        "turn": turn_num,
                        "actor": "World",
                        "outcome": event_outcome,
                        "is_world_event": True
                        # Other fields like plan, moods, reflection will be None by default or ommitted if not applicable
                    }
                    full_simulation_log.append(event_log_entry)
                    current_scene_log_entries.append(event_log_entry) # Add to scene log for judge_scene_end
                    world_agent.update_from_outcome(event_outcome) # Update world state from event outcome

                if turn_num >= world_agent.max_scene_turns: # Add a hard stop for scene turns
                     logger.warning(f"Scene {scene_num + 1} reached max turns ({world_agent.max_scene_turns}). Ending scene.")
                     break


            # End of scene
            logger.info(f"Scene {scene_num + 1} ended.")
            
            # Choose POV character for narration
            pov_character_name, pov_character_info = world_agent.choose_pov_character_for_scene()
            logger.info(f"Narrating scene {scene_num + 1} from POV of: {pov_character_name}")
            
            # Narrate the scene
            # The narrator needs a list of factual outcomes.
            # current_scene_factual_outcomes needs to be structured correctly.
            # The log_for_narrator in systemPatterns was a list of dicts. Let's adapt.
            # For now, Narrator.render expects a list of factual outcome strings.
            # We will use current_scene_factual_outcomes which is List[str]
            # narrator_log = [] 
            # for entry in full_simulation_log:
            #     if entry.get("scene") == scene_num +1: # filter for current scene
            #         # Narrator needs actor, outcome, and mood_during_action.
            #         # We might need to adjust what's passed or how Narrator formats it.
            #         # For now, let's pass a simplified list of outcome strings.
            #         # This part needs alignment with Narrator.render() expectations.
            #         # For now, passing the simple list of strings:
            #         pass # current_scene_factual_outcomes is already a list of strings

            # Ensure pov_character_info is structured as expected by Narrator
            # Example: {"persona": "...", "goals": [...], "mood": MoodVector}
            # pov_character_info from world_agent might be CharacterState or similar
            
            if pov_character_name and pov_character_info:
                prose = narrator.render(
                    scene_log=current_scene_log_entries, # Changed argument name
                    pov_character_name=pov_character_name,
                    pov_character_info=pov_character_info # Ensure this matches Narrator's expectation
                )
                full_story_prose.append(prose)
                logger.info(f"Scene {scene_num + 1} narration:\n{prose}")
            else:
                logger.warning(f"Could not determine POV character for scene {scene_num + 1}. Skipping narration.")
                full_story_prose.append(f"== Scene {scene_num + 1} (Narration Skipped) ==\n")

            # Memory: Summarise scene
            logger.debug(f"Summarizing scene {scene_num + 1} for memory...")
            memory_manager.summarise_scene(scene_num + 1, current_scene_log_entries) # Pass List[LogEntry dict]

        logger.info("\n--- Simulation Finished ---")

        # Save the full story
        story_file_path = output_dir / "story.md"
        with open(story_file_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(full_story_prose))
        logger.info(f"Full story saved to: {story_file_path}")

        # Save the detailed simulation log
        log_file_path = output_dir / "simulation_log.jsonl"
        with open(log_file_path, 'w', encoding='utf-8') as f:
            for entry in full_simulation_log:
                json.dump(entry, f)
                f.write('\n')
        logger.info(f"Detailed simulation log saved to: {log_file_path}")

        print(f"\nSimulation complete. Story written to {story_file_path}")
        
    except FileNotFoundError as e:
        logger.error(f"Error: {e}", exc_info=args.debug)
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}", exc_info=args.debug)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.debug)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 