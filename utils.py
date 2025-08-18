"""
Utility functions for Alexa Wine Skill
Includes input validation, logging, and helper functions
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Logger:
    """Logger utility with different log levels"""
    
    @staticmethod
    def info(message: str, data: Optional[Dict] = None) -> None:
        """Log info message with optional data"""
        if config.LOG_LEVEL in ['info', 'debug']:
            if data:
                try:
                    logger.info(f"{message}: {json.dumps(data, default=str)}")
                except Exception:
                    # Fallback: stringify dict items defensively
                    safe = {str(k): str(v) for k, v in data.items()}
                    logger.info(f"{message}: {json.dumps(safe)}")
            else:
                logger.info(message)
    
    @staticmethod
    def error(message: str, error: Optional[Exception] = None) -> None:
        """Log error message with optional exception"""
        if error:
            logger.error(f"{message}: {str(error)}", exc_info=True)
        else:
            logger.error(message)
    
    @staticmethod
    def debug(message: str, data: Optional[Dict] = None) -> None:
        """Log debug message with optional data"""
        if config.LOG_LEVEL == 'debug':
            if data:
                try:
                    logger.debug(f"{message}: {json.dumps(data, default=str)}")
                except Exception:
                    safe = {str(k): str(v) for k, v in data.items()}
                    logger.debug(f"{message}: {json.dumps(safe)}")
            else:
                logger.debug(message)

class Validation:
    """Input validation utilities"""
    
    @staticmethod
    def validate_wine_name(wine_name: str) -> Dict[str, Any]:
        """
        Validates and sanitizes wine name input
        
        Args:
            wine_name: The wine name to validate
            
        Returns:
            Dict with isValid, sanitized, and optional error
        """
        if not wine_name or not isinstance(wine_name, str):
            return {'is_valid': False, 'error': 'Wine name is required'}
        
        # Remove potentially harmful characters and trim
        sanitized = re.sub(r'[<>"\'&]', '', wine_name.strip())
        
        if not sanitized:
            return {'is_valid': False, 'error': 'Wine name is required'}
        
        if len(sanitized) > 100:
            return {'is_valid': False, 'error': 'Wine name is too long'}
        
        return {'is_valid': True, 'sanitized': sanitized}
    
    @staticmethod
    def validate_action(action: str) -> Dict[str, Any]:
        """
        Validates action type for wine details
        
        Args:
            action: The action to validate
            
        Returns:
            Dict with isValid, sanitized, and optional error
        """
        if not action or not isinstance(action, str):
            return {'is_valid': False, 'error': 'Action is required'}
        
        sanitized = action.lower().strip()
        valid_actions = list(config.DETAIL_TYPES.values())
        
        if sanitized not in valid_actions:
            return {
                'is_valid': False,
                'error': f"Invalid action. Valid actions are: {', '.join(valid_actions)}"
            }
        
        return {'is_valid': True, 'sanitized': sanitized}

class SlotUtils:
    """Slot extraction utilities with validation"""
    
    @staticmethod
    def get_wine_from_intent(intent: Dict, use_default: bool = False) -> Dict[str, Any]:
        """
        Safely extracts wine name from intent slots
        
        Args:
            intent: The Alexa intent object
            use_default: Whether to use default wine if none provided
            
        Returns:
            Dict with success, value, and optional error
        """
        try:
            wine_slot = intent.get('slots', {}).get('Wine')
            
            if not wine_slot or not wine_slot.get('value'):
                if use_default:
                    return {
                        'success': True,
                        'value': 'Goldeneye Pinot Noir Confluence 2014'
                    }
                return {'success': False, 'error': 'No wine specified'}
            
            validation_result = Validation.validate_wine_name(wine_slot['value'])
            if not validation_result['is_valid']:
                return {'success': False, 'error': validation_result['error']}
            
            return {'success': True, 'value': validation_result['sanitized']}
            
        except Exception as error:
            Logger.error('Error extracting wine from intent', error)
            return {'success': False, 'error': 'Failed to process wine name'}
    
    @staticmethod
    def get_action_from_intent(intent: Dict) -> Dict[str, Any]:
        """
        Safely extracts action from intent slots
        
        Args:
            intent: The Alexa intent object
            
        Returns:
            Dict with success, value, and optional error
        """
        try:
            action_slot = intent.get('slots', {}).get('Action')
            
            if not action_slot or not action_slot.get('value'):
                return {'success': False, 'error': 'No action specified'}
            
            validation_result = Validation.validate_action(action_slot['value'])
            if not validation_result['is_valid']:
                return {'success': False, 'error': validation_result['error']}
            
            return {'success': True, 'value': validation_result['sanitized']}
            
        except Exception as error:
            Logger.error('Error extracting action from intent', error)
            return {'success': False, 'error': 'Failed to process action'}
    
    @staticmethod
    def get_date_from_intent(intent: Dict) -> Dict[str, Any]:
        """
        Safely extracts date from intent slots
        
        Args:
            intent: The Alexa intent object
            
        Returns:
            Dict with success, display_date, request_date_param, and optional error
        """
        try:
            from datetime import datetime
            
            date_slot = intent.get('slots', {}).get('Date')
            
            if not date_slot or not date_slot.get('value'):
                # Default to current year
                now = datetime.now()
                return {
                    'success': True,
                    'display_date': "Today",
                    'request_date_param': now.year
                }
            
            try:
                date = datetime.fromisoformat(date_slot['value'].replace('Z', '+00:00'))
            except ValueError:
                return {'success': False, 'error': 'Invalid date format'}
            
            return {
                'success': True,
                'display_date': date.strftime('%B %d, %Y'),
                'request_date_param': date.year
            }
            
        except Exception as error:
            Logger.error('Error extracting date from intent', error)
            return {'success': False, 'error': 'Failed to process date'}

class SessionUtils:
    """Session attribute utilities for state management"""
    
    @staticmethod
    def get_wine_list(attributes_manager) -> List[Dict]:
        """
        Safely gets wine list from session attributes
        
        Args:
            attributes_manager: Alexa attributes manager
            
        Returns:
            List of wines or empty list
        """
        try:
            attributes = attributes_manager.session_attributes
            return attributes.get('wine_list', [])
        except Exception as error:
            Logger.error('Error getting wine list from session', error)
            return []
    
    @staticmethod
    def set_wine_list(attributes_manager, wine_list: List[Dict]) -> None:
        """
        Safely sets wine list in session attributes
        
        Args:
            attributes_manager: Alexa attributes manager
            wine_list: List of wines to store
        """
        try:
            attributes_manager.session_attributes['wine_list'] = wine_list or []
        except Exception as error:
            Logger.error('Error setting wine list in session', error)
    
    @staticmethod
    def get_current_wine_index(attributes_manager) -> int:
        """
        Safely gets current wine index from session attributes
        
        Args:
            attributes_manager: Alexa attributes manager
            
        Returns:
            Current wine index or 0
        """
        try:
            attributes = attributes_manager.session_attributes
            return attributes.get('current_wine_index', 0)
        except Exception as error:
            Logger.error('Error getting current wine index from session', error)
            return 0
    
    @staticmethod
    def set_current_wine_index(attributes_manager, index: int) -> None:
        """
        Safely sets current wine index in session attributes
        
        Args:
            attributes_manager: Alexa attributes manager
            index: Wine index to store
        """
        try:
            attributes_manager.session_attributes['current_wine_index'] = index or 0
        except Exception as error:
            Logger.error('Error setting current wine index in session', error)

# Create utility instances
logger_util = Logger()
validation = Validation()
slot_utils = SlotUtils()
session_utils = SessionUtils()
