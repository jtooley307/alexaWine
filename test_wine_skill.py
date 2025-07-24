"""
Test suite for Alexa Wine Skill Python implementation
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
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
    
    @pytest.mark.asyncio
    async def test_handle_wine_search_success(self):
        """Test successful wine search"""
        handler = WineSearchIntentHandler()
        handler_input = Mock(spec=HandlerInput)
        handler_input.request_envelope = Mock()
        handler_input.request_envelope.request = Mock()
        handler_input.request_envelope.request.intent = Mock()
        handler_input.request_envelope.request.intent.to_dict.return_value = {
            'slots': {'Wine': {'value': 'Pinot Noir'}}
        }
        handler_input.attributes_manager = Mock()
        handler_input.response_builder = Mock()
        handler_input.response_builder.speak.return_value = handler_input.response_builder
        handler_input.response_builder.ask.return_value = handler_input.response_builder
        handler_input.response_builder.set_card.return_value = handler_input.response_builder
        
        mock_wine = {
            'Name': 'Test Pinot Noir',
            'Winery': 'Test Winery',
            'Price': 25.99,
            'Rating': 4.5
        }
        
        with patch.object(WineService, 'search_wines', return_value=[mock_wine]):
            response = await handler.handle(handler_input)
            
            handler_input.response_builder.speak.assert_called()
            handler_input.response_builder.ask.assert_called()

class TestWineService:
    """Test cases for WineService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_database = {
            'wines': [
                {
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
            ],
            'metadata': {'version': '1.0'}
        }
    
    @patch('wine_service.os.path.join')
    @patch('builtins.open')
    @patch('wine_service.json.load')
    def test_load_wine_database_success(self, mock_json_load, mock_open, mock_path_join):
        """Test successful wine database loading"""
        mock_json_load.return_value = self.mock_database
        mock_path_join.return_value = '/path/to/wineDatabase.json'
        
        service = WineService()
        
        assert service.wine_database == self.mock_database
        mock_open.assert_called_once()
        mock_json_load.assert_called_once()
    
    @patch('wine_service.os.path.join')
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_wine_database_failure(self, mock_open, mock_path_join):
        """Test wine database loading failure"""
        with pytest.raises(Exception, match="Wine database could not be loaded"):
            WineService()
    
    @pytest.mark.asyncio
    async def test_search_wines_success(self):
        """Test successful wine search"""
        service = WineService()
        service.wine_database = self.mock_database
        
        results = await service.search_wines('Pinot Noir')
        
        assert len(results) == 1
        assert results[0]['Name'] == 'Test Pinot Noir'
        assert results[0]['Winery'] == 'Test Winery'
    
    @pytest.mark.asyncio
    async def test_search_wines_empty_term(self):
        """Test wine search with empty search term"""
        service = WineService()
        service.wine_database = self.mock_database
        
        with pytest.raises(ValueError, match="Invalid search term provided"):
            await service.search_wines('')
    
    @pytest.mark.asyncio
    async def test_search_wines_with_filters(self):
        """Test wine search with filters"""
        service = WineService()
        service.wine_database = self.mock_database
        
        results = await service.search_wines('wine', {'max_price': 30.0})
        
        assert len(results) == 1
        assert results[0]['Price'] == 25.99
    
    def test_process_wine_data(self):
        """Test wine data processing"""
        service = WineService()
        service.wine_database = self.mock_database
        
        raw_wine = self.mock_database['wines'][0]
        processed = service.process_wine_data(raw_wine)
        
        assert processed['Name'] == 'Test Pinot Noir'
        assert processed['Winery'] == 'Test Winery'
        assert processed['Price'] == 25.99
        assert processed['Rating'] == 4.5

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
        mock_manager.session_attributes = {'wine_list': [{'Name': 'Test Wine'}]}
        
        result = session_utils.get_wine_list(mock_manager)
        
        assert len(result) == 1
        assert result[0]['Name'] == 'Test Wine'
    
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
