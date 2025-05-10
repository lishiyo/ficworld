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

from modules.config_loader import ConfigLoader


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
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        print(f"Loading preset: {args.preset}")
        config = config_loader.load_full_preset(args.preset)
        
        # Set up output directory
        output_dir = setup_output_directory(args.preset, args.output_dir)
        print(f"Output will be saved to: {output_dir}")
        
        # Save configuration for reference
        with open(output_dir / 'config_used.json', 'w', encoding='utf-8') as f:
            json.dump({
                "preset_name": args.preset,
                "world_name": config["world"].world_name,
                "roles": [role.archetype_name for role in config["roles"]],
                "mode": config["preset"].mode,
                "max_scenes": config["preset"].max_scenes,
                "llm": config["preset"].llm
            }, f, indent=2)
        
        # Display loaded configuration
        print("\nLoaded Configuration:")
        print(f"World: {config['world'].world_name}")
        print(f"Roles: {', '.join(role.archetype_name for role in config['roles'])}")
        print(f"Simulation Mode: {config['preset'].mode}")
        print(f"Max Scenes: {config['preset'].max_scenes}")
        print(f"LLM: {config['preset'].llm}")
        
        # TODO: Initialize LLM Interface
        # TODO: Initialize Memory Manager
        # TODO: Initialize World Agent
        # TODO: Initialize Character Agents
        # TODO: Initialize Narrator
        # TODO: Run simulation loop
        
        print("\nInitial setup complete. Full simulation not yet implemented.")
        print("This is just the configuration loading step.")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 