# Contributing to RAG AI Agent

Thank you for considering contributing to this project! 🎉

## How to Contribute

### Reporting Issues

- Check if the issue already exists
- Use the issue template
- Provide detailed information:
  - Environment (OS, Python version, Node version)
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages and logs

### Suggesting Features

- Open an issue with the `enhancement` label
- Describe the feature and its use case
- Explain how it would benefit users

### Code Contributions

#### Getting Started

1. **Fork the repository**
   ```bash
   git clone https://github.com/YPT-ME/AIAgent.git
   cd AIAgent
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**
   ```bash
   # Backend
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   
   # Frontend
   cd ../frontend
   pnpm install
   ```

4. **Make your changes**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new features
   - Update documentation

5. **Test your changes**
   ```bash
   # Backend tests
   cd backend
   pytest tests/ -v
   pytest --cov=src
   
   # Linting
   black src tests
   ruff check src tests
   mypy src
   
   # Frontend
   cd ../frontend
   pnpm lint
   pnpm format:check
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `style:` Code style changes
   - `refactor:` Code refactoring
   - `test:` Adding tests
   - `chore:` Maintenance tasks

7. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Pull Request Guidelines

- **Title**: Clear and descriptive
- **Description**: 
  - What changes were made
  - Why these changes are needed
  - Related issues (use `Closes #123`)
- **Testing**: Describe how you tested
- **Screenshots**: Include for UI changes
- **Documentation**: Update README if needed

### Code Style

#### Python (Backend)
- Follow PEP 8
- Use `black` for formatting
- Use `ruff` for linting
- Use type hints
- Write docstrings for functions

#### TypeScript (Frontend)
- Follow the project's ESLint config
- Use Prettier for formatting
- Use meaningful variable names
- Write JSDoc comments for complex functions

### Project Structure

```
backend/
├── src/
│   ├── agent/          # LangGraph agent logic
│   ├── ingestion/      # Document processing
│   ├── analytics/      # Analytics & monitoring
│   └── middleware/     # Security & validation
└── tests/              # Unit and integration tests

frontend/
├── src/
│   ├── app/           # Next.js pages
│   ├── components/    # React components
│   └── lib/           # Utilities
```

### Testing

- Write tests for new features
- Maintain test coverage above 80%
- Test edge cases and error handling
- Use fixtures for test data

### Documentation

- Update README.md for new features
- Add docstrings to Python functions
- Comment complex logic
- Include usage examples

## Development Guidelines

### Backend Development

- Use type hints for all functions
- Handle errors gracefully
- Log important events
- Follow async/await patterns
- Keep functions small and focused

### Frontend Development

- Use TypeScript strictly
- Follow React best practices
- Keep components small
- Use proper state management
- Optimize performance

### Security

- Never commit secrets or API keys
- Validate all user inputs
- Sanitize data before storage
- Follow security best practices
- Report security issues privately

## Community

- Be respectful and inclusive
- Help others in discussions
- Share knowledge and ideas
- Give constructive feedback

## Questions?

- Open an [Issue](https://github.com/YPT-ME/AIAgent/issues)
- Email: developer@ypt.me
- Check existing issues and PRs
- Read the documentation

Thank you for contributing! 🚀
