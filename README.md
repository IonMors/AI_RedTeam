# AI Red Team POC

## Installation (Windows PowerShell)

Run these commands from the project directory with Python 3.11 or 3.12.

### 1. Create and activate a virtual environment

Use the project-local `.venv` directory. This project was verified on Python 3.11 and 3.12.

```pwsh
py -3.12 -m venv .venv
.\venv\Scripts\Activate.ps1
```

### 2. Install project dependencies

```pwsh
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .
```

The editable installation makes `copilot_model` and `target` importable in this virtual environment without setting `$env:PYTHONPATH`. Source edits take effect without reinstalling. The project dependencies, including `sentry-sdk` and `posthog`, are declared in `pyproject.toml`; `requirements.txt` provides the environment snapshot. The Copilot SDK is pinned to 1.0.34 because newer major versions change its Python API.

### 3. Install the telemetry dependencies explicitly

```pwsh
python -m pip install sentry-sdk posthog
```

This avoids missing-import issues when evaluation libraries pull in telemetry packages transitively. The pip package name is `sentry-sdk`, but the Python import is `sentry_sdk`.

### 4. Verify the installation

```pwsh
python -c "import sentry_sdk; import posthog; import deepeval; print('Dependencies import successfully')"
```

## Copilot configuration

This project uses your existing GitHub Copilot subscription through the official Copilot SDK, not through a custom OpenAI-compatible endpoint. Model access, usage limits, and organization policy still apply.

Install the official [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-getting-started), sign in with the account that owns the subscription, and verify the available model IDs before running local evaluations. Complete authentication on the machine where the project runs; do not paste tokens into chat or commit them.

Add the following non-secret settings to your local `.env` file (see `.env.example`):

```dotenv
COPILOT_MODEL=gpt-5
COPILOT_TIMEOUT_SECONDS=120
```

Set `COPILOT_MODEL` to the model ID available to your account. The adapter defaults to these values when they are not present. Existing shell environment variables take precedence over `.env` values. If necessary, set `COPILOT_CLI_PATH` to a compatible CLI executable and `COPILOT_HOME` to a custom local storage directory.

The adapter opens a fresh empty session for each model call and disables tools, repository config discovery, hooks, skills, memory, and local file access. This keeps the evaluation isolated and text-only. Keep prompts free of real customer data or secrets.

## Run the project

Run a small live model test first to confirm the Copilot adapter is working:

```pwsh
python src/smoke_test_copilot.py
```

Start the local target in one terminal:

```pwsh
python -m uvicorn target.app:app --host 127.0.0.1 --port 8000
```

In a second terminal, activate the same virtual environment and run the YAML campaign from the project root:

```pwsh
python -m deepteam run .\redteam.yaml
```

Keep the target bound to localhost. The campaign is intentionally adversarial and generates reports under `reports/milestone2`.

Run the offline adapter tests without needing live Copilot authentication or model use:

```pwsh
python -m pytest tests/test_copilot_model.py -q
```

## Build and dependency maintenance

Build a wheel from the project directory:

```pwsh
python -m pip wheel . --no-deps --wheel-dir dist
```

The wheel artifact is written to `dist/` and contains the project packages, not local secrets, reports, or the root YAML campaign file. For local development, the editable install is usually the easiest option because the adapter resolves `.env` relative to the source tree.

To refresh the dependency snapshot after a successful install, run:

```pwsh
python -m pip freeze --exclude ai-redteam-poc | Set-Content -Path requirements.txt -Encoding utf8
```

> Note: the stale `deepteam==1.0.10` pin was invalid because that package is not published on PyPI. Use the current project venv and reinstall from the verified dependency set if you hit a package-not-found error.
