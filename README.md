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

4. Create a `.env` file in the project root and add your API keys:
```
OPENROUTER_API_KEY=your_openai_api_key
# Add other API keys as needed
```

## Usage

1. Run a simulation with a specific preset:
```bash
python main.py --preset demo_forest_run
```

2. Check the generated story output in the `outputs/` directory.

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