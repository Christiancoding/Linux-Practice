"""
Practice Controller - Business Logic Management

Handles practice operations with enhanced error handling
and integration with modern learning algorithms.
"""

import logging
from typing import Optional, Dict, List, Any
from services.vm_service import VMIntegrationService

logger = logging.getLogger(__name__)

class PracticeController:
    """Enhanced practice controller with modern architecture."""
    
    def __init__(self):
        """Initialize practice controller with VM support."""
        self.logger = logging.getLogger(__name__)
        self.vm_service: VMIntegrationService = VMIntegrationService()
        self.logger.info("PracticeController initialized with VM support")
    
    def get_practice_modes(self) -> List[str]:
        """Get available practice modes including VM environments."""
        return ["quiz", "flashcards", "vm_practice", "simulation"]
    
    def start_vm_practice(self, user_id: int, challenge_type: str) -> Any:
        """Start VM-based practice session."""
        try:
            return self.vm_service.start_practice_session(user_id, challenge_type)
        except Exception as e:
            self.logger.error(f"Failed to start VM practice: {e}")
            raise
