"""
Test suite for Alexa Wine Skill Python implementation
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import RequestEnvelope, LaunchRequest, IntentRequest, Intent, Slot
from ask_sdk_model.ui import SimpleCard

from lambda_function import (
    LaunchRequestHandler,
    WineSearchIntentHandler,
    WineActionDetailIntentHandler,
    NextIntentHandler,
    PreviousIntentHandler,
    CatchAllExceptionHandler
)
from wine_service import WineService
from utils import validation, slot_utils, session_utils
from config import config

class TestLaunchRequestHandler:
    """Test cases for LaunchRequestHandler"""
    
    def test_can_handle_launch_request(self):
        """Test that handler can handle LaunchRequest"""
        handler = LaunchRequestHandler()
        handler_input = Mock(spec=HandlerInput)
        handler_input.request_envelope = Mock()
        handler_input.request_envelope.request = Mock(spec=LaunchRequest)
        handler_input.request_envelope.request.object_type = "LaunchRequest"
        
        assert handler.can_handle(handler_input) is True
    
    def test_handle_launch_request(self):
        """Test launch request handling"""
        handler = LaunchRequestHandler()
        handler_input = Mock(spec=HandlerInput)
        handler_input.response_builder = Mock()
        handler_input.response_builder.speak.return_value = handler_input.response_builder
        handler_input.response_builder.ask.return_value = handler_input.response_builder
        handler_input.response_builder.set_card.return_value = handler_input.response_builder
        
        response = handler.handle(handler_input)
        
        handler_input.response_builder.speak.assert_called_once_with(config.MESSAGES['welcome'])
        handler_input.response_builder.ask.assert_called_once_with(config.MESSAGES['welcome_reprompt'])

class TestWineSearchIntentHandler:
    """Test cases for WineSearchIntentHandler"""
    
    def test_can_handle_wine_search_intent(self):
        """Test that handler can handle wineSearchIntent"""
        handler = WineSearchIntentHandler()
        handler_input = Mock(spec=HandlerInput)
        handler_input.request_envelope = Mock()
        handler_input.request_envelope.request = Mock(spec=IntentRequest)
        handler_input.request_envelope.request.object_type = "IntentRequest"
        handler_input.request_envelope.request.intent = Mock(spec=Intent)
        handler_input.request_envelope.request.intent.name = "wineSearchIntent"
        
        assert handler.can_handle(handler_input) is True
    
    @patch('lambda_function.wine_service')  # Patch the global wine_service in lambda_function
    @patch('lambda_function.config')
    def test_handle_wine_search_success(self, mock_config, mock_wine_service):
        """Test successful wine search"""
        # Setup mock configuration
        mock_config.MESSAGES = {
            'no_wine_provided': 'Please specify a wine to search for.',
            'wine_not_found': 'Sorry, I could not find any wines matching your search.',
            'ask_again': 'You can ask for the price, rating, location, or description. What would you like to know?',
            'general_error': 'Sorry, something went wrong.',
            'api_error': 'Sorry, there was an issue with the wine service.'
        }
        mock_config.ALEXA_CARD_TITLE = 'Wine Finder'
        
        # Setup the mock wine service (lowercase keys per handler expectations)
        mock_wine = {
            'name': 'Test Pinot Noir',
            'winery': 'Test Winery',
            'price': 25.99,
            'rating': 4.5
        }
        
        # Configure the mock to return our test wine (sync)
        mock_wine_service.search_wines = MagicMock(return_value=[mock_wine])
        
        # Initialize the handler
        handler = WineSearchIntentHandler()
        
        # Create a mock for the response builder
        mock_response_builder = MagicMock()
        mock_response_builder.speak.return_value = mock_response_builder
        mock_response_builder.ask.return_value = mock_response_builder
        mock_response_builder.set_card.return_value = mock_response_builder
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response_builder.response = mock_response
        
        # Setup handler input with wine slot
        handler_input = MagicMock(spec=HandlerInput)
        handler_input.request_envelope = MagicMock()
        handler_input.request_envelope.request = MagicMock()
        handler_input.request_envelope.request.intent = MagicMock()
        handler_input.request_envelope.request.intent.slots = {
            'Wine': MagicMock(value='Pinot Noir')
        }
        handler_input.request_envelope.request.intent.to_dict.return_value = {
            'slots': {'Wine': {'value': 'Pinot Noir'}}
        }
        
        # Setup attributes manager with session attributes
        session_attrs = {}
        handler_input.attributes_manager = MagicMock()
        handler_input.attributes_manager.session_attributes = session_attrs
        handler_input.response_builder = mock_response_builder
        
        # Call the handler (synchronously)
        response = handler.handle(handler_input)
        
        # Verify the response is built correctly
        mock_response_builder.speak.assert_called_once()
        mock_response_builder.ask.assert_called_once()
        mock_response_builder.set_card.assert_called_once()
        
        # Verify search_wines was called with the correct arguments
        mock_wine_service.search_wines.assert_called_once_with('Pinot Noir')
        
        # Verify session attributes were set correctly (lowercase keys)
        assert 'wine_list' in session_attrs, "wine_list not set in session attributes"
        assert len(session_attrs['wine_list']) == 1, "Expected one wine in wine_list"
        assert session_attrs['wine_list'][0]['name'] == 'Test Pinot Noir', "Incorrect wine in wine_list"
        assert 'current_wine_index' in session_attrs, "current_wine_index not set in session attributes"
        assert session_attrs['current_wine_index'] == 0, "Incorrect current_wine_index"

class TestWineService:
    """Test cases for WineService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Raw wine data as it would come from the database
        self.raw_wine_data = {
            'name': 'Test Pinot Noir',
            'winery': 'Test Winery',
            'type': 'Red Wine',
            'region': 'Napa Valley',
            'country': 'USA',
            'price': 25.99,
            'rating': 4.5,
            'description': 'A delicious red wine',
            'pairings': ['beef', 'cheese'],
            'occasions': ['dinner', 'celebration']
        }
        
        # Processed wine data as expected by the service (lowercase keys)
        self.processed_wine_data = {
            'name': 'Test Pinot Noir',
            'winery': 'Test Winery',
            'type': 'Red Wine',
            'region': 'Napa Valley',
            'price': 25.99,
            'rating': 4.5,
            'description': 'A delicious red wine'
        }
        
        # Mock database with raw wine data
        self.mock_database = {
            'wines': [self.raw_wine_data],
            'metadata': {'version': '1.0'}
        }
    
    @patch('wine_service.os.path.join')
    @patch('builtins.open')
    @patch('wine_service.json.load')
    def test_load_wine_database_success(self, mock_json_load, mock_open, mock_path_join):
        """Test successful wine database loading"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_open.return_value = mock_file
        mock_json_load.return_value = self.mock_database
        mock_path_join.return_value = '/path/to/wine_data.json'
        
        # Create service which will trigger database load
        service = WineService()
        
        # Verify the database was loaded correctly
        assert service.wine_database == self.mock_database
        
        # Verify the file was opened (can be called multiple times due to context manager)
        assert mock_open.call_count >= 1
        mock_open.assert_any_call('/path/to/wine_data.json', 'r', encoding='utf-8')
        mock_json_load.assert_called_with(mock_file)
    
    @patch('wine_service.os.path.join')
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_wine_database_failure(self, mock_open, mock_path_join):
        """Test wine database loading failure"""
        mock_path_join.return_value = '/path/to/wine_data.json'
        
        # Create service - should not raise an exception
        service = WineService()
        
        # Should initialize with empty wine list on failure
        assert service.wine_database == {'wines': []}
        # Verify at least one attempt to open the file was made
        assert mock_open.call_count >= 1
        mock_open.assert_any_call('/path/to/wine_data.json', 'r', encoding='utf-8')
    
    @pytest.mark.asyncio
    @patch('wine_service.WineAPIService')
    @patch('wine_service.WineService.load_wine_database')
    async def test_search_wines_success(self, mock_load_db, mock_wine_api):
        """Test successful wine search"""
        # Create a mock for the search_wines method (sync)
        mock_api_instance = mock_wine_api.return_value
        mock_api_instance.search_wines = MagicMock(return_value=[])
        
        # Create service with mocked database
        service = WineService()
        service.wine_database = self.mock_database
        
        # Patch the process_wine_data method to return our processed data
        with patch.object(service, 'process_wine_data', return_value=self.processed_wine_data):
            # Test search
            results = service.search_wines('Pinot Noir')
            
            # Verify results - should find our test wine in the local database
            assert len(results) == 1
            assert results[0]['name'] == 'Test Pinot Noir'
            assert results[0]['winery'] == 'Test Winery'
    
    @pytest.mark.asyncio
    @patch('wine_service.WineAPIService')
    async def test_search_wines_empty_term(self, mock_wine_api):
        """Test wine search with empty search term"""
        mock_api_instance = mock_wine_api.return_value
        
        service = WineService()
        service.wine_database = self.mock_database
        
        with pytest.raises(ValueError, match="Invalid search term provided"):
            service.search_wines('')
    
    @pytest.mark.asyncio
    @patch('wine_service.WineAPIService')
    @patch('wine_service.WineService.load_wine_database')
    async def test_search_wines_with_filters(self, mock_load_db, mock_wine_api):
        """Test wine search with filters"""
        # Create a mock for the search_wines method (sync)
        mock_api_instance = mock_wine_api.return_value
        mock_api_instance.search_wines = MagicMock(return_value=[])
        
        # Create service with mocked database
        service = WineService()
        service.wine_database = self.mock_database
        
        # Patch the process_wine_data method to return our processed data
        with patch.object(service, 'process_wine_data', return_value=self.processed_wine_data):
            # Test search with price filter - should match our test wine
            results = service.search_wines('wine', {'max_price': 30.0})
            
            # Should find our test wine in the local database
            assert len(results) == 1
            assert results[0]['name'] == 'Test Pinot Noir'
            assert results[0]['price'] == 25.99
    
    def test_process_wine_data(self):
        """Test wine data processing"""
        service = WineService()
        
        raw_wine = self.mock_database['wines'][0]
        processed = service.process_wine_data(raw_wine)
        
        assert processed['name'] == 'Test Pinot Noir'
        assert processed['winery'] == 'Test Winery'
        assert processed['price'] == 25.99
        assert processed['rating'] == 4.5

class TestValidation:
    """Test cases for validation utilities"""
    
    def test_validate_wine_name_success(self):
        """Test successful wine name validation"""
        result = validation.validate_wine_name('Pinot Noir')
        
        assert result['is_valid'] is True
        assert result['sanitized'] == 'Pinot Noir'
    
    def test_validate_wine_name_empty(self):
        """Test wine name validation with empty input"""
        result = validation.validate_wine_name('')
        
        assert result['is_valid'] is False
        assert 'required' in result['error']
    
    def test_validate_wine_name_too_long(self):
        """Test wine name validation with too long input"""
        long_name = 'a' * 101
        result = validation.validate_wine_name(long_name)
        
        assert result['is_valid'] is False
        assert 'too long' in result['error']
    
    def test_validate_wine_name_sanitization(self):
        """Test wine name sanitization"""
        result = validation.validate_wine_name('Pinot<script>alert("xss")</script>Noir')
        
        assert result['is_valid'] is True
        assert '<script>' not in result['sanitized']
    
    def test_validate_action_success(self):
        """Test successful action validation"""
        result = validation.validate_action('price')
        
        assert result['is_valid'] is True
        assert result['sanitized'] == 'price'
    
    def test_validate_action_invalid(self):
        """Test action validation with invalid action"""
        result = validation.validate_action('invalid_action')
        
        assert result['is_valid'] is False
        assert 'Invalid action' in result['error']

class TestSlotUtils:
    """Test cases for slot utilities"""
    
    def test_get_wine_from_intent_success(self):
        """Test successful wine extraction from intent"""
        intent = {
            'slots': {
                'Wine': {'value': 'Pinot Noir'}
            }
        }
        
        result = slot_utils.get_wine_from_intent(intent)
        
        assert result['success'] is True
        assert result['value'] == 'Pinot Noir'
    
    def test_get_wine_from_intent_no_slot(self):
        """Test wine extraction with no wine slot"""
        intent = {'slots': {}}
        
        result = slot_utils.get_wine_from_intent(intent)
        
        assert result['success'] is False
        assert 'No wine specified' in result['error']
    
    def test_get_wine_from_intent_use_default(self):
        """Test wine extraction with default fallback"""
        intent = {'slots': {}}
        
        result = slot_utils.get_wine_from_intent(intent, use_default=True)
        
        assert result['success'] is True
        assert 'Goldeneye' in result['value']
    
    def test_get_action_from_intent_success(self):
        """Test successful action extraction from intent"""
        intent = {
            'slots': {
                'Action': {'value': 'price'}
            }
        }
        
        result = slot_utils.get_action_from_intent(intent)
        
        assert result['success'] is True
        assert result['value'] == 'price'

class TestSessionUtils:
    """Test cases for session utilities"""
    
    def test_get_wine_list_success(self):
        """Test successful wine list retrieval"""
        mock_manager = Mock()
        mock_manager.session_attributes = {'wine_list': [{'name': 'Test Wine'}]}
        
        result = session_utils.get_wine_list(mock_manager)
        
        assert len(result) == 1
        assert result[0]['name'] == 'Test Wine'

class TestDynamoDBBackend:
    """Tests for DynamoDB-backed search integration in WineService."""

    @patch('wine_service.WineAPIService')
    @patch('wine_service.WineDynamoDBService')
    def test_search_uses_dynamodb_when_enabled(self, mock_dynamo_cls, mock_api_cls):
        # Enable DynamoDB in config
        from wine_service import WineService
        from config import config as cfg
        original_flag = getattr(cfg, 'USE_DYNAMODB', False)
        try:
            setattr(cfg, 'USE_DYNAMODB', True)

            # Mock DynamoDB service instance
            mock_dynamo = mock_dynamo_cls.return_value
            mock_dynamo.search_wines.return_value = [
                {
                    'wine_id': 1,
                    'name': 'Dyn Pinot Noir',
                    'winery': 'Dyn Winery',
                    'type': 'red',
                    'region': 'Willamette Valley',
                    'country': 'USA',
                    'price': 29.99,
                    'rating': 4.6
                }
            ]
            # API should not be called if Dynamo returns results
            mock_api = mock_api_cls.return_value
            mock_api.search_wines.return_value = []

            service = WineService()
            # Force DynamoDB backend to our mock instance to ensure path is taken
            service.dynamo = mock_dynamo
            # service.search_wines is sync; just call it
            results = service.search_wines('Pinot Noir')

            assert len(results) == 1
            assert results[0]['name'] == 'Dyn Pinot Noir'
            assert results[0]['winery'] == 'Dyn Winery'
            mock_dynamo.search_wines.assert_called_once()
        finally:
            setattr(cfg, 'USE_DYNAMODB', original_flag)
    
    def test_get_wine_list_empty(self):
        """Test wine list retrieval with empty session"""
        mock_manager = Mock()
        mock_manager.session_attributes = {}
        
        result = session_utils.get_wine_list(mock_manager)
        
        assert result == []
    
    def test_set_wine_list_success(self):
        """Test successful wine list setting"""
        mock_manager = Mock()
        mock_manager.session_attributes = {}
        wine_list = [{'Name': 'Test Wine'}]
        
        session_utils.set_wine_list(mock_manager, wine_list)
        
        assert mock_manager.session_attributes['wine_list'] == wine_list
    
    def test_get_current_wine_index_success(self):
        """Test successful wine index retrieval"""
        mock_manager = Mock()
        mock_manager.session_attributes = {'current_wine_index': 2}
        
        result = session_utils.get_current_wine_index(mock_manager)
        
        assert result == 2
    
    def test_get_current_wine_index_default(self):
        """Test wine index retrieval with default value"""
        mock_manager = Mock()
        mock_manager.session_attributes = {}
        
        result = session_utils.get_current_wine_index(mock_manager)
        
        assert result == 0

if __name__ == '__main__':
    pytest.main([__file__])
