# Resume Builder

AI-assisted resume generation for LaTeX resumes built with Python, Jinja2, and a keyboard-only terminal CLI.

This project renders resume templates from structured YAML data, compiles them with `latexmk`, and supports an AI review loop that maps a job description to bullet selections before generation.

## Features

- Render LaTeX resumes from modular Jinja2 templates under `templates/resume/`
- Generate every run into a new timestamped folder under `generated/resumes/`
- Compile PDF output with `latexmk`
- Use a keyboard-only interactive CLI built with `prompt_toolkit`
- Run manual selection or AI-assisted selection
- Review AI suggestions before generation
- Save an `generation_summary.txt` artifact for accepted AI generations
- Keep configuration in `config.yaml`
- Keep OpenRouter credentials in `.env`

## Tech Stack

- Python 3.11+
- Jinja2
- PyYAML
- prompt_toolkit
- Pydantic
- LangGraph
- LangChain OpenAI-compatible client
- OpenRouter
- LaTeX + `latexmk`

## Repository Structure

```text
.
├── app/
│   ├── ai/                 # OpenRouter client, LangGraph prompt/graph, AI service
│   ├── interactive/        # Keyboard-only CLI UI
│   ├── cli.py              # Console entrypoint
│   ├── compiler.py         # latexmk integration
│   ├── config.py           # config.yaml load/save/defaults
│   ├── data_loader.py      # YAML loading and validation
│   ├── generation_summary.py
│   ├── models.py
│   ├── pipeline.py         # generation pipeline orchestration
│   ├── renderer.py         # Jinja2 -> LaTeX rendering
│   └── selection.py        # manual selection, validation, render context application
├── data/
│   ├── profiles/           # Stable resume structure and constraints
│   └── bullets/            # Selectable summary/bullet inventory
├── templates/resume/       # Source LaTeX templates
├── generated/resumes/      # Generated runs
├── tests/
├── config.yaml
└── pyproject.toml
```

## How It Works

The pipeline is:

1. Load config from `config.yaml`
2. Load a profile from `data/profiles/`
3. Load a bullet library from `data/bullets/`
4. Select content manually or via AI
5. Validate selection constraints
6. Build the final render context
7. Render LaTeX into a new output folder
8. Optionally compile the PDF with `latexmk`
9. Save an AI generation summary when the run came from an accepted AI review

## Data Model

### Profiles

Files in `data/profiles/` define the stable resume structure:

- contact information
- education
- skills
- certificates
- experience entry definitions
- project entry definitions
- selection constraints

Each experience/project entry includes stable metadata plus `min_bullets` and `max_bullets`.

The profile itself also defines:

- `min_experience_entries`
- `max_experience_entries`
- `min_project_entries`
- `max_project_entries`

### Bullet Libraries

Files in `data/bullets/` define the selectable content inventory:

- `summary_options`
- `experience`
- `projects`

Each bullet has a stable `id`, `text`, and optional `tags`.

The AI and manual flows both operate on bullet IDs, not free-form text.

## Template Syntax

The LaTeX templates use native Jinja delimiters configured for LaTeX-friendly rendering:

- variables: `[[ value ]]`
- blocks: `[% if condition %] ... [% endif %]`
- comments: `[# comment #]`

This avoids conflicts with normal LaTeX braces.

## Installation

### 1. Create an environment

```bash
conda create -n resume python=3.12
conda activate resume
```

### 2. Install the project

```bash
python -m pip install -e .
```

### 3. Install LaTeX tooling

PDF generation requires `latexmk`.

Examples:

```bash
# macOS
brew install --cask mactex-no-gui

# Ubuntu / Debian
sudo apt-get update
sudo apt-get install latexmk texlive-latex-extra texlive-fonts-recommended
```

If `latexmk` is not installed, the app raises a clear compiler error with install guidance.

### 4. Configure OpenRouter

The interactive CLI will guide you on first launch, but you can also create `.env` manually:

```env
OPENROUTER_API_KEY=your_key_here
```

Default AI model:

```text
openai/gpt-5.4-mini
```

## Configuration

The app stores local settings in `config.yaml`.

Current config keys:

- `template_root`
- `data_root`
- `output_root`
- `active_profile`
- `active_bullet_library`
- `compile_pdf`
- `openrouter_model`
- `openrouter_base_url`
- `setup_completed`

## Usage

### Interactive CLI

Launch the keyboard-only CLI:

```bash
resume-builder cli
```

Top-level actions:

- `generate using ai`
- `generate manually`
- `edit config`
- `exit`

Key bindings:

```text
up/down or j/k  move
enter           select or submit
space           toggle bullets in manual selection
esc             go back
q               quit
ctrl+u          clear current input line
```

Notes:

- Job description input is single-line and visually wraps inside the box
- Feedback input is single-line and visually wraps inside the box
- Input boxes expand with wrapped content up to 4 rows

### Direct Generation

Generate from the command line without entering the interactive UI:

```bash
resume-builder generate
```

Override the defaults:

```bash
resume-builder generate \
  --profile profiles/general.yaml \
  --bullet-library bullets/general.yaml
```

Render LaTeX without compiling a PDF:

```bash
resume-builder generate --no-compile
```

## AI Workflow

The AI flow uses LangGraph with OpenRouter through an OpenAI-compatible API.

The interaction loop is:

1. Select a profile
2. Select a bullet library
3. Enter a job description
4. Let the AI propose a structured bullet selection
5. Review the selection in the CLI
6. Accept it or provide revision feedback
7. Generate the final resume

The AI is constrained by the profile schema and selection rules:

- only valid entry IDs and bullet IDs may be used
- experience entry counts must stay within profile min/max
- project entry counts must stay within profile min/max
- each selected entry must satisfy its min/max bullet constraints

If the AI returns an invalid suggestion, the service retries with explicit validation feedback before surfacing an error.

## Generated Output

Each run creates a new folder under:

```text
generated/resumes/resume-YYYYMMDD-HHMMSS/
```

Typical contents:

- `main.tex`
- `sections/*.tex`
- `main.pdf` when PDF compilation is enabled
- `generation_summary.txt` for accepted AI generations

## Testing

Run the full test suite:

```bash
python -m unittest discover -s tests -v
```

The test suite covers:

- config load/save
- YAML schema loading
- selection validation
- rendering
- compile behavior
- interactive CLI flow
- AI retry behavior
- pipeline output generation

## Development Notes

- The current LaTeX template source of truth lives in `templates/resume/`
- The codebase is structured to leave room for more advanced AI agents later
- The current AI step selects and optionally rewrites bullets, but the user remains in the review loop before generation

## License

No license file is currently included in this repository.
