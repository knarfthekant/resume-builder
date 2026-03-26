Activating conda environment:
```bash
conda create -n resume python=3.12
conda activate resume
```

Install the app dependencies:
```bash
python3 -m pip install -e .
```

Run the CLI:
```bash
resume-builder generate
resume-builder cli
```

Interactive CLI keys:
```text
up/down or j/k : move
enter          : select or save
esc            : go back
q              : quit
```
