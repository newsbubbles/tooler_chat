# Contributing to Tooler Chat

Thank you for considering contributing to Tooler Chat! This document outlines the process for contributing to this project.

## Development Workflow

### Branching Strategy

We use a simplified Git Flow workflow:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/xxx`: Feature branches
- `bugfix/xxx`: Bug fix branches

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/tooler-chat.git`
3. Set up the development environment using `./setup.sh`
4. Create a feature branch from `develop`: `git checkout -b feature/your-feature develop`

### Making Changes

1. Make your changes in your feature branch
2. Follow the coding conventions and style guides
3. Write or update tests as necessary
4. Ensure all tests pass
5. Update documentation if needed

### Submitting Changes

1. Push your changes to your fork: `git push origin feature/your-feature`
2. Open a pull request against the `develop` branch
3. Describe your changes in detail
4. Reference any related issues

## Code Standards

### Backend (Python)

- Follow PEP 8 style guide
- Use type hints where applicable
- Write docstrings for functions and classes
- Keep functions short and focused

### Frontend (React)

- Follow ESLint configuration
- Use TypeScript types/interfaces
- Use functional components with hooks
- Keep components small and reusable

## Testing

- Write unit tests for backend services
- Write component tests for React components
- All PRs should maintain or increase test coverage

## Documentation

- Update README.md with any new features or changed functionality
- Document API endpoints using OpenAPI/Swagger
- Include comments for complex logic

## Pull Request Process

1. Ensure your PR includes tests for new functionality
2. Update the documentation if needed
3. The PR must pass all CI checks
4. Get review approval from at least one maintainer
5. Your PR will be merged by a maintainer

## Code of Conduct

Please be respectful and considerate of others when contributing. We aim to foster an inclusive and welcoming community.

## Getting Help

If you have questions or need assistance, please:

- Open an issue with the "question" label
- Reach out to the maintainers

Thank you for contributing to Tooler Chat!
