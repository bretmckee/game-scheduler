# Developer Documentation

Welcome to the Game Scheduler developer documentation. This guide covers everything you need to contribute to the project, from environment setup to architecture understanding.

## Getting Started

### Development Environment

**[Development Setup Guide](SETUP.md)** - Complete environment setup, development workflow, and pre-commit hooks

Quick start:
```bash
# Clone and start development environment
git clone <repository-url>
cd game-scheduler
docker compose up
```

## Architecture & Design

**[System Architecture](architecture.md)** - Microservices architecture, communication patterns, and design decisions

Overview:
- Discord Bot Service - Gateway interactions and notifications
- Web API Service - FastAPI REST API for dashboard
- Notification Daemon - Event-driven game reminders
- Status Transition Daemon - Event-driven status updates
- PostgreSQL - Primary data store with LISTEN/NOTIFY
- RabbitMQ - Message broker for inter-service communication
- Redis - Caching and session storage

**[Database Schema](database.md)** - Entity-relationship diagrams, Row-Level Security (RLS), and guild isolation

**[OAuth Flow](oauth-flow.md)** - Discord OAuth2 authentication sequence and token management

**[Transaction Management](transaction-management.md)** - Service layer patterns, transaction scoping, and consistency

**[Deferred Event Publishing](deferred-events.md)** - Event-driven architecture for notifications and status transitions

**[Production Readiness: Guild Isolation](production-readiness.md)** - Multi-tenant security with Row-Level Security

**[Docker Compose Dependencies](compose-dependencies.md)** - Service dependency graph and startup orchestration

## Testing

**[Testing Guide](TESTING.md)** - Comprehensive testing documentation covering unit, integration, and end-to-end tests

Test types:
- **Unit Tests** - Fast, isolated component tests
- **Integration Tests** - Service integration with database/message broker
- **End-to-End Tests** - Full system tests with Discord bot interactions

Quick commands:
```bash
# Run unit tests
pre-commit run pytest-all --hook-stage manual

# Run integration tests
scripts/run-integration-tests.sh

# Run E2E tests
scripts/run-e2e-tests.sh
```

## Development Tools

**[Cloudflare Tunnel Setup](cloudflare-tunnel.md)** - Local development with public HTTPS endpoints for OAuth testing

**[Local GitHub Actions Testing](local-act-testing.md)** - Run CI/CD workflows locally with `act` before pushing

## Contributing Guidelines

### Code Quality Standards

The project enforces comprehensive code quality through:

- **Ruff** - Python linting with 33 rule categories (security, correctness, performance)
- **ESLint** - Frontend linting with React and TypeScript plugins
- **Prettier** - Code formatting for JavaScript/TypeScript/CSS
- **MyPy** - Python type checking
- **Complexipy** - Python complexity analysis (max complexity: 10)
- **Lizard** - Frontend complexity analysis
- **JSCPD** - Duplicate code detection

See [SETUP.md](SETUP.md) for pre-commit hook configuration.

### Code Style

- **Python**: Follow PEP 8, use type annotations, prefer modern Python 3.13+ syntax
- **TypeScript**: Follow project ESLint configuration, use strict TypeScript settings
- **Comments**: Write self-explanatory code, comment only when necessary to explain WHY (see `.github/instructions/self-explanatory-code-commenting.instructions.md`)
- **Commit Messages**: Use conventional commit format when appropriate

### Pull Request Process

1. Create feature branch from `main`
2. Make changes following code quality standards
3. Ensure all pre-commit hooks pass
4. Run relevant test suites locally
5. Submit PR with clear description of changes
6. Address review feedback
7. CI/CD pipeline must pass before merge

### Security Practices

- Never commit secrets or credentials
- Use environment variables for configuration
- Follow least-privilege principles in database/API design
- Review security-related linting rules (flake8-bandit)
- Test authorization logic thoroughly

## Additional Resources

- [Root README](../../README.md) - Project overview and quick links
- [Deployment Documentation](../deployment/README.md) - Self-hosting and production deployment
- [Guild Admin Guide](../GUILD-ADMIN.md) - Bot setup and configuration
- [Host Guide](../HOST-GUIDE.md) - Game management workflows
- [Player Guide](../PLAYER-GUIDE.md) - End-user interactions

## Questions or Issues?

- Check existing documentation first
- Review related code and tests for examples
- Open an issue on GitHub for bugs or feature requests
- Submit a PR for documentation improvements
