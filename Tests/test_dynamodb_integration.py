import os
import pytest

from config import config as cfg
from wine_service import WineService


pytestmark = pytest.mark.integration


def env_bool(val: str) -> bool:
    return str(val or '').lower() in ('1', 'true', 'yes', 'y')


@pytest.mark.skipif(
    not env_bool(os.getenv('USE_DYNAMODB')) and not env_bool(os.getenv('RUN_DYNAMO_INTEGRATION')),
    reason='DynamoDB integration test skipped: set USE_DYNAMODB=true or RUN_DYNAMO_INTEGRATION=1'
)
def test_dynamodb_search_returns_results_and_lowercase_keys():
    # Ensure service uses DynamoDB regardless of prior config
    original_flag = getattr(cfg, 'USE_DYNAMODB', False)
    try:
        setattr(cfg, 'USE_DYNAMODB', True)

        # Optionally allow targeting alternative endpoint (e.g., DynamoDB Local)
        # via DYNAMODB_ENDPOINT_URL which wine_dynamodb_service.py honors.
        # Requires AWS credentials/config for real AWS.

        # Require the caller to provide a search term known to exist in their dataset
        search_term = os.getenv('DYNAMO_TEST_SEARCH_TERM')
        if not search_term:
            pytest.skip('Set DYNAMO_TEST_SEARCH_TERM to run this integration test against real data')

        service = WineService()
        results = service.search_wines(search_term)

        # We expect at least one result from the existing tables for the provided term
        assert isinstance(results, list)
        assert len(results) >= 1, 'Expected at least one wine from DynamoDB for the provided search term'

        # Validate lowercase keys normalization
        sample = results[0]
        # minimal keys we expect
        for key in ['name', 'type', 'winery']:
            assert key in sample, f'Missing normalized key: {key}'

        # No TitleCase keys should be present
        assert all(not any(ch.isupper() for ch in k) for k in sample.keys()), 'Found non-lowercase keys in result'

    finally:
        setattr(cfg, 'USE_DYNAMODB', original_flag)
