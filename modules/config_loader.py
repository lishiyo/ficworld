"""
Configuration loader for FicWorld.
Handles loading presets, world definitions, and role archetypes from JSON files.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import (
    Preset, WorldDefinition, RoleArchetype, Location, ScriptBeat, 
    WorldEvent, GlobalLore, FactionInfo
)


class ConfigLoader:
    """
    Loads and parses configuration files for FicWorld simulations.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the ConfigLoader with the base directory.
        
        Args:
            base_dir: Path to the FicWorld base directory. If None, uses the current working directory.
        """
        self.base_dir = Path(base_dir or os.getcwd())
        self.presets_dir = self.base_dir / "presets"
        self.worlds_dir = self.base_dir / "data" / "worlds"
        self.roles_dir = self.base_dir / "data" / "roles"
    
    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Returns:
            Dict containing the parsed JSON.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file isn't valid JSON.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {str(e)}", e.doc, e.pos)
    
    def load_preset(self, preset_name: str) -> Preset:
        """
        Load a preset configuration.
        
        Args:
            preset_name: Name of the preset (without extension).
            
        Returns:
            Preset object containing the configuration.
            
        Raises:
            FileNotFoundError: If the preset file doesn't exist.
        """
        if not preset_name.endswith('.json'):
            preset_name += '.json'
        
        preset_path = self.presets_dir / preset_name
        preset_data = self.load_json(preset_path)
        
        # Create and return a Preset object
        return Preset(
            world_file=preset_data.get('world_file'),
            role_files=preset_data.get('role_files', []),
            mode=preset_data.get('mode', 'free'),
            max_scenes=preset_data.get('max_scenes', 3),
            llm=preset_data.get('llm', 'deepseek/deepseek-r1:free'),
            script_file=preset_data.get('script_file')
        )
    
    def load_world_definition(self, world_file: str) -> WorldDefinition:
        """
        Load a world definition.
        
        Args:
            world_file: Path to the world definition file (e.g., "test_world.json" or "worlds/test_world.json").
            
        Returns:
            WorldDefinition object.
            
        Raises:
            FileNotFoundError: If the world file doesn't exist.
        """
        # Ensure .json extension
        if not world_file.endswith('.json'):
            world_file += '.json'
        
        # Get the bare filename, removing potential directory prefixes
        bare_world_file = world_file.split('/')[-1]
        
        world_path = self.worlds_dir / bare_world_file
        world_data = self.load_json(world_path)
        
        # Parse locations
        locations = []
        for loc_data in world_data.get('locations', []):
            locations.append(Location(
                id=loc_data.get('id'),
                name=loc_data.get('name'),
                description=loc_data.get('description'),
                connections=loc_data.get('connections', [])
            ))
        
        # Parse script beats
        beats = []
        for beat_data in world_data.get('script_beats', []):
            beats.append(ScriptBeat(
                scene_id=beat_data.get('scene_id'),
                beat_id=beat_data.get('beat_id'),
                description=beat_data.get('description'),
                triggers_event=beat_data.get('triggers_event'),
                required_location=beat_data.get('required_location')
            ))
        
        # Parse world events
        events = []
        for event_data in world_data.get('world_events_pool', []):
            events.append(WorldEvent(
                event_id=event_data.get('event_id'),
                description=event_data.get('description'),
                effects=event_data.get('effects', [])
            ))
        
        # Parse global lore
        lore_data = world_data.get('global_lore', {})
        factions = []
        for faction_data in lore_data.get('key_factions', []):
            factions.append(FactionInfo(
                name=faction_data.get('name'),
                details=faction_data.get('details')
            ))
        
        global_lore = GlobalLore(
            magic_system=lore_data.get('magic_system'),
            key_factions=factions
        )
        
        # Create and return WorldDefinition
        return WorldDefinition(
            world_name=world_data.get('world_name'),
            description=world_data.get('description'),
            locations=locations,
            global_lore=global_lore,
            script_beats=beats,
            world_events_pool=events
        )
    
    def load_role_archetype(self, role_file: str) -> RoleArchetype:
        """
        Load a role archetype.
        
        Args:
            role_file: Path to the role archetype file (e.g., "test_role.json" or "roles/test_role.json").
            
        Returns:
            RoleArchetype object.
            
        Raises:
            FileNotFoundError: If the role file doesn't exist.
        """
        # Ensure .json extension
        if not role_file.endswith('.json'):
            role_file += '.json'
            
        # Get the bare filename, removing potential directory prefixes
        bare_role_file = role_file.split('/')[-1]

        role_path = self.roles_dir / bare_role_file
        role_data = self.load_json(role_path)
        
        # Create and return RoleArchetype
        return RoleArchetype(
            archetype_name=role_data.get('archetype_name'),
            persona_template=role_data.get('persona_template'),
            goal_templates=role_data.get('goal_templates', []),
            starting_mood_template=role_data.get('starting_mood_template', {}),
            activity_coefficient=role_data.get('activity_coefficient', 0.5),
            icon=role_data.get('icon')
        )
    
    def load_full_preset(self, preset_name: str) -> Dict[str, Any]:
        """
        Load a preset and all its associated world and role files.
        
        Args:
            preset_name: Name of the preset (without extension).
            
        Returns:
            Dictionary containing the preset, world definition, and role archetypes.
        """
        preset = self.load_preset(preset_name)
        world = self.load_world_definition(preset.world_file)
        roles = [self.load_role_archetype(role_file) for role_file in preset.role_files]
        
        return {
            "preset": preset,
            "world": world,
            "roles": roles
        } 