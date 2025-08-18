# Alexa Wine Skill - Python Implementation

A modernized Python implementation of the Alexa Wine Skill with enhanced security, error handling, and maintainability.

## Features

- **Secure Configuration**: Environment variable management with `.env` support
- **Robust Error Handling**: Comprehensive error handling with user-friendly messages
- **Input Validation**: Sanitization and validation of all user inputs
- **Session Management**: Proper session state management
- **Structured Logging**: Configurable logging levels with structured output
- **Local Wine Database**: Curated wine database with smart search capabilities
- **Modern Python**: Built with ASK SDK for Python v1.19+

## Architecture

### Core Modules

- `lambda_function.py` - Main entry point with Alexa intent handlers
- `wine_service.py` - Wine database operations and search functionality
- `utils.py` - Validation, logging, and session management utilities
- `config.py` - Configuration management with environment variables

### Intent Handlers

- **LaunchRequest** - Welcome message when skill is opened
- **WineSearchIntent** - Search for wines by name, type, or winery
- **WineActionDetailIntent** - Get specific wine details (price, rating, location, description)
- **GetWineDetailsIntent** - Ask what details user wants to know
- **NextIntent/PreviousIntent** - Navigate through search results
- **StartOverIntent** - Reset to first wine in results
- **HelpIntent** - Provide usage instructions
- **CancelAndStopIntent** - Exit the skill

## Setup Instructions

### Prerequisites

- Python 3.9+
- AWS CLI configured
- Serverless Framework (for deployment)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/alexaWine
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Install serverless plugins (for deployment):**
   ```bash
   npm install serverless-python-requirements
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Wine API Configuration
WINE_API_KEY=your_wine_api_key_here
WINE_API_BASE_URL=https://services.wine.com/api/beta2/service.svc/JSON

# Alexa Skill Configuration
ALEXA_SKILL_ID=your_alexa_skill_id_here

# AWS Configuration
AWS_REGION=us-east-1
LOG_LEVEL=info
```

### Testing

Run the test suite:

```bash
# Run all tests
python -m pytest test_wine_skill.py -v

# Run with coverage
python -m pytest test_wine_skill.py --cov=. --cov-report=html

# Run specific test class
python -m pytest test_wine_skill.py::TestWineService -v
```

### Deployment

Deploy to AWS Lambda using Serverless Framework:

```bash
# Deploy to development stage
serverless deploy --config serverless-python.yml

# Deploy to production stage
serverless deploy --config serverless-python.yml --stage prod
```

## OpenSearch Integration (BM25, Vector, Hybrid)

- __Prereqs__:
  - OpenSearch domain and index (e.g., `xwines-vec-768-1k`) with `knn_vector` field `embedding` of dim 768.
  - Local Ollama running with `nomic-embed-text` for query-time embeddings.

- __.env settings__:
  - `OPENSEARCH_ENDPOINT=https://<your-domain>`
  - `OPENSEARCH_INDEX=xwines-vec-768-1k`
  - `OPENSEARCH_USE_IAM=true` (recommended)
  - `USE_OPENSEARCH=true`
  - `USE_VECTOR_SEARCH=true` to enable kNN
  - `USE_HYBRID_SEARCH=true` to fuse BM25 + kNN (reciprocal rank)
  - `OLLAMA_BASE_URL=http://localhost:11434`
  - `OLLAMA_EMBED_MODEL=nomic-embed-text`

- __Notes__:
  - With IAM enabled, ensure AWS credentials are available to the process (ENV/Sso/Instance profile).
  - Hybrid search runs BM25 and kNN, merging results for improved relevance.
  - Set `USE_VECTOR_SEARCH=false` to fall back to BM25 only.

## Data Ingestion with Embeddings

Use `ingest_xwines_vectors.py` to create the index and bulk-ingest wines with embeddings:

```bash
python ingest_xwines_vectors.py --csv /path/to/XWines_Slim_1K_wines.csv --index xwines-vec-768-1k --chunk-size 200
```

The script supports the slim CSV schema (e.g., `WineID`, `WineName`, `WineryName`, `RegionName`, `Grapes`, `Harmonize`, `ABV`).

## Usage Examples

### Voice Commands

- "Alexa, open Wine Assistant"
- "Find a Pinot Noir"
- "What's the price of this wine?"
- "Tell me about the rating"
- "Where is this wine from?"
- "Next wine"
- "Previous wine"
- "Start over"

### Supported Wine Details

- **Price** - Get the wine's price
- **Rating** - Get the wine's rating out of 5 stars
- **Location** - Get the wine's region and country
- **Description** - Get detailed wine description

## Security Features

- **Input Sanitization**: All user inputs are validated and sanitized
- **Environment Variables**: Sensitive data stored securely
- **HTTPS Only**: All external API calls use HTTPS
- **Error Handling**: Generic error messages prevent information leakage
- **Session Security**: Proper session attribute management

## Error Handling

The skill includes comprehensive error handling for:

- Invalid user inputs
- Wine database failures
- Network timeouts
- Session management errors
- Unexpected exceptions

## Database Structure

The local wine database (`wineDatabase.json`) contains:

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2024-01-01"
  },
  "wines": [
    {
      "name": "Wine Name",
      "winery": "Winery Name",
      "type": "Red Wine",
      "region": "Napa Valley",
      "country": "USA",
      "price": 25.99,
      "rating": 4.5,
      "description": "Wine description",
      "pairings": ["beef", "cheese"],
      "occasions": ["dinner", "celebration"],
      "vintage": "2020",
      "alcohol_content": "14.5%"
    }
  ]
}
```

## Migration from Node.js

This Python implementation maintains full feature parity with the original Node.js version while adding:

- Modern Python async/await patterns
- Enhanced type hints and documentation
- Improved error handling and logging
- Better test coverage
- Cleaner code organization

## Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Include docstrings for all classes and methods
4. Write tests for new functionality
5. Update this README for any new features

## License

This project is licensed under the MIT License.
