# FicWorld

FicWorld is a multi-agent storytelling system that generates coherent narratives through interactions between autonomous character agents with emotion, private reasoning, and memory.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/ficworld.git
cd ficworld
```

2. Create and activate a Python virtual environment (Python 3.10+ recommended):
```bash
python -m venv venv312
source venv312/bin/activate  # On Windows: venv312\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your API keys. FicWorld primarily uses OpenRouter, so ensure your OpenRouter key is set:
```
OPENROUTER_API_KEY=your_openrouter_api_key
# Add other API keys if other LLM providers are configured in presets
```

## Usage

To run a simulation, use the `main.py` script with the `--preset` argument specifying the name of a preset file located in the `presets/` directory (without the `.json` extension).

**Examples:**

1. Run a simulation with a specific preset (e.g., `demo_forest_run.json`):
   ```bash
   python main.py --preset demo_forest_run
   ```

2. Run in debug mode for more verbose logging:
   ```bash
   python main.py --preset demo_forest_run --debug
   ```

3. Specify a custom output directory:
   ```bash
   python main.py --preset demo_forest_run --output-dir outputs/my_custom_run
   ```

Outputs, including the generated story (`story.md`) and a detailed simulation log (`simulation_log.jsonl`), will be saved in a directory under `outputs/` (e.g., `outputs/demo_forest_run/`) unless a custom output directory is specified.

## Project Structure

- `data/` - Input data (worlds, roles, prompts)
- `presets/` - Configuration files for simulation runs
- `modules/` - Core Python modules
- `outputs/` - Generated stories and logs

## Features

- **Emergent storytelling** through autonomous character agents
- **Emotional memory retrieval** based on character moods
- **Two-layer agent thought process** (private reflection → public action)
- **Separation of simulation and narration**
- **Config-driven approach** for reproducible story generation

## License

[MIT License](LICENSE) 