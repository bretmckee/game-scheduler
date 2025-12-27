# Configuration Templates

This directory contains template configuration files for the Game Scheduler application.

## Purpose

These templates serve as starting points for new deployments. They contain:

- `env.template` - Environment variable template with documentation for all settings
- `grafana-alloy/` - Grafana Alloy observability configuration and dashboards
- `rabbitmq/` - RabbitMQ message broker configuration

## Usage for New Deployments

When setting up a new deployment:

1. Copy the entire `config.template/` directory to `config/`:
   ```bash
   cp -r config.template config
   ```

2. Navigate to the config directory and initialize a git repository:
   ```bash
   cd config
   git init
   ```

3. Copy `env.template` to your environment-specific files:
   ```bash
   cp env.template env.dev      # Development environment
   cp env.template env.staging  # Staging environment
   cp env.template env.prod     # Production environment
   ```

4. Edit each environment file with your specific configuration values

5. Commit your configuration:
   ```bash
   git add .
   git commit -m "Initial configuration"
   ```

6. Optionally, push to a private repository to backup your configs

## Security Note

The `config/` directory is git-ignored in the main repository to prevent accidentally committing sensitive credentials. Your private configuration repository in `config/` allows you to version control your environment-specific settings separately and securely.
