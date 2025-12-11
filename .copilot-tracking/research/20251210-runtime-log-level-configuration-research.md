<!-- markdownlint-disable-file -->
# Task Research Notes: Runtime Log Level Configuration

## Research Executed

### File Analysis
- `services/api/main.py`
  - Currently uses `config.log_level` from environment variable
  - Calls `setup_logging(config.log_level)` which uses `logging.basicConfig()`
  - No command-line argument parsing present
- `services/bot/main.py`
  - Similar pattern: reads `config.log_level` from BotConfig (pydantic)
  - Calls `setup_logging(config.log_level)` 
  - No command-line argument parsing present
- `services/scheduler/notification_daemon_wrapper.py` and `status_transition_daemon_wrapper.py`
  - Use `os.getenv("LOG_LEVEL", "INFO")` directly
  - Call `logging.basicConfig()` with level from environment
  - No command-line argument parsing present

### Code Search Results
- All services currently support LOG_LEVEL environment variable
- No services currently use argparse for command-line options
- Configuration loaded at module initialization time
- All services use similar `setup_logging(log_level: str)` pattern

### External Research
- #fetch:https://docs.python.org/3/library/argparse.html
  - Standard library for parsing command-line arguments
  - Supports `--log-level` or `-v/--verbose` patterns
  - Can specify choices to restrict valid values
  - Example: `parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])`
- #fetch:https://docs.python.org/3/howto/logging.html
  - Recommends using `getattr(logging, loglevel.upper())` to convert string to level
  - Environment variables already widely used for configuration
  - Log level can be changed at runtime but requires code support

### Project Conventions
- Standards referenced: `.github/instructions/python.instructions.md`
  - Use modern Python 3.13+ type hints
  - Use pydantic for validation
  - Keep functions focused and concise
- Instructions followed: `.github/instructions/coding-best-practices.instructions.md`
  - Modularity and DRY principles apply
  - Configuration should be explicit and validated

## Key Discoveries

### Current Implementation Pattern
All Python services follow this pattern:
```python
def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
```

### Environment Variable Support
- API service: `APIConfig.log_level` from `LOG_LEVEL` env var (default: "INFO")
- Bot service: `BotConfig.log_level` from `LOG_LEVEL` env var (default: "INFO")  
- Scheduler daemons: `os.getenv("LOG_LEVEL", "INFO")` directly
- Docker compose: `LOG_LEVEL: ${LOG_LEVEL:-INFO}` with fallback

### Project Dependencies
From `pyproject.toml`:
- No CLI parsing libraries currently included
- Could use standard library `argparse` (zero dependencies)
- Pydantic already available for validation

## Recommended Approach

### Implementation Strategy
Add **optional** command-line argument support that **overrides** environment variable if provided, maintaining backward compatibility:

**Priority order:**
1. Command-line argument (highest priority, most explicit)
2. Environment variable (current behavior)
3. Default value (lowest priority)

### Complete Implementation Pattern

```python
import argparse
import logging
import os
import sys

def create_argument_parser(prog_name: str, description: str) -> argparse.ArgumentParser:
    """
    Create argument parser with log level option.
    
    Args:
        prog_name: Program name for help display
        description: Program description
        
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (overrides LOG_LEVEL environment variable)",
    )
    
    return parser

def get_log_level(
    cli_log_level: str | None,
    env_var_name: str = "LOG_LEVEL",
    default: str = "INFO",
) -> str:
    """
    Determine log level from CLI args, environment, or default.
    
    Priority: CLI argument > Environment variable > Default
    
    Args:
        cli_log_level: Log level from command-line argument (None if not provided)
        env_var_name: Environment variable name to check
        default: Default log level if neither CLI nor env var provided
        
    Returns:
        Log level string (uppercase)
    """
    if cli_log_level is not None:
        return cli_log_level.upper()
    
    env_level = os.getenv(env_var_name)
    if env_level is not None:
        return env_level.upper()
    
    return default.upper()

def setup_logging(log_level: str) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

async def main() -> None:
    """Entry point with argument parsing."""
    # Parse command-line arguments
    parser = create_argument_parser(
        prog_name="api-service",
        description="Discord Game Scheduler API Service"
    )
    args = parser.parse_args()
    
    # Load config (existing code)
    config = get_api_config()
    
    # Determine log level: CLI > Config (env var) > default
    log_level = get_log_level(
        cli_log_level=args.log_level,
        env_var_name="LOG_LEVEL",
        default=config.log_level,  # Config already has env var or default
    )
    
    setup_logging(log_level)
    # ... rest of main()
```

### Application to Each Service

#### API Service (`services/api/main.py`)
- Add `create_argument_parser()` and `get_log_level()` utility functions
- Modify `main()` to parse args before loading config
- Pass resolved log level to `setup_logging()`

#### Bot Service (`services/bot/main.py`)
- Same pattern as API service
- Use bot-specific program name and description

#### Scheduler Daemons
- `notification_daemon_wrapper.py` and `status_transition_daemon_wrapper.py`
- Add argparse support with same pattern
- Currently use `os.getenv("LOG_LEVEL", "INFO")` directly

### Docker Integration
No changes needed to Docker files - environment variables continue to work:
```yaml
environment:
  LOG_LEVEL: ${LOG_LEVEL:-INFO}
```

Users can override at runtime:
```bash
# Using environment variable (current)
LOG_LEVEL=DEBUG docker compose up

# Using command-line in custom entrypoint/CMD
docker compose run api --log-level DEBUG

# Local development
uv run python -m services.api.main --log-level DEBUG
```

## Implementation Guidance

**Objectives:**
- Make log level configurable at runtime via CLI without rebuilding
- Maintain backward compatibility with LOG_LEVEL environment variable
- Follow consistent pattern across all services
- Provide helpful CLI help messages

**Key Tasks:**
1. Add `create_argument_parser()` helper function to each service's main.py
2. Add `get_log_level()` helper to resolve priority order
3. Update each `main()` function to parse arguments
4. Update tests to verify CLI argument handling
5. Update documentation with new CLI option usage

**Dependencies:**
- No new package dependencies (uses stdlib `argparse`)
- Requires changes to 4 main.py files

**Success Criteria:**
- `python -m services.api.main --log-level DEBUG` works
- `python -m services.api.main --help` shows log level option
- Environment variable LOG_LEVEL still works when CLI arg not provided
- CLI argument overrides environment variable when both present
- All existing tests pass
- Docker deployment continues to work unchanged

## Grafana Alloy Log Level Configuration

### Research Executed

#### External Documentation
- #fetch:https://grafana.com/docs/alloy/latest/reference/config-blocks/logging/
  - Alloy supports `logging` configuration block with `level` parameter
  - Valid levels: "error", "warn", "info", "debug"
  - Format: "json" or "logfmt"
  - Configuration uses Alloy's native `env()` function to read environment variables

#### Current Implementation
- File: `grafana-alloy/config.alloy`
  - Hardcoded: `level = "info"`
  - Already uses `env()` for other config (endpoints, credentials)
  - Logging config at lines 12-16

#### Docker Configuration  
- File: `docker-compose.base.yml`
  - Service: `grafana-alloy`
  - Currently no LOG_LEVEL or ALLOY_LOG_LEVEL environment variable
  - Uses command line: `run --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data /etc/alloy/config.alloy`

### Implementation Pattern for Alloy

Alloy configuration uses the `env()` function to read environment variables:

```alloy
logging {
  level    = env("ALLOY_LOG_LEVEL")
  format   = "json"
  write_to = [loki.write.grafana_cloud_loki.receiver]
}
```

However, `env()` requires the variable to exist. For optional environment variables with defaults, Alloy uses `coalesce(env("VAR"), "default")`:

```alloy
logging {
  level    = coalesce(env("ALLOY_LOG_LEVEL"), "info")
  format   = "json"
  write_to = [loki.write.grafana_cloud_loki.receiver]
}
```

### Docker Compose Integration

Add environment variable to `grafana-alloy` service:

```yaml
grafana-alloy:
  image: grafana/alloy:latest
  environment:
    ALLOY_LOG_LEVEL: ${ALLOY_LOG_LEVEL:-info}
    # ... existing environment variables
```

### Usage Examples

```bash
# Using environment variable in docker-compose
ALLOY_LOG_LEVEL=debug docker compose up grafana-alloy

# Setting in .env file
echo "ALLOY_LOG_LEVEL=debug" >> .env

# Override for single service
docker compose run -e ALLOY_LOG_LEVEL=debug grafana-alloy
```

### Implementation Tasks

1. Update `grafana-alloy/config.alloy`:
   - Change `level = "info"` to `level = coalesce(env("ALLOY_LOG_LEVEL"), "info")`

2. Update `docker-compose.base.yml`:
   - Add `ALLOY_LOG_LEVEL: ${ALLOY_LOG_LEVEL:-info}` to grafana-alloy service environment

3. Update `.env.example`:
   - Add `ALLOY_LOG_LEVEL=info` with comment

### Valid Log Levels for Alloy
- `error` - Only error level logs
- `warn` - Warning and above
- `info` - Info and above (default)
- `debug` - All logs including debug

### Success Criteria
- `ALLOY_LOG_LEVEL=debug docker compose up` changes Alloy's log verbosity
- Default remains "info" when variable not set
- Environment variable can be set in `.env` file
- No rebuild required to change log level
