#!/usr/bin/env python3
"""
Test analytics system to verify SQLAlchemy session management fixes.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_analytics_import():
    """Test if analytics integration can be imported without errors."""
    try:
        print("Testing analytics import...")
        from services.analytics_integration import WebAnalyticsTracker, track_page_view
        print("✓ Analytics integration imported successfully")
        return True
    except Exception as e:
        print(f"✗ Analytics import failed: {e}")
        return False

def test_analytics_disabled():
    """Test analytics system with disabled flag."""
    try:
        print("\nTesting analytics with disabled flag...")
        
        # Set environment variable to disable analytics
        os.environ['ANALYTICS_ENABLED'] = 'false'
        
        # Import after setting environment variable
        from services.analytics_integration import track_page_view
        
        # This should not fail even if called
        track_page_view("test_page")
        print("✓ Analytics tracking with disabled flag works")
        return True
    except Exception as e:
        print(f"✗ Analytics disabled test failed: {e}")
        return False

def test_database_manager():
    """Test if database manager can be initialized."""
    try:
        print("\nTesting database manager...")
        from utils.database import initialize_database_pool, get_database_manager
        
        # Initialize database pool
        db_manager = initialize_database_pool(db_type="sqlite", enable_pooling=False)
        print("✓ Database manager initialized")
        
        # Test session creation
        with db_manager.get_session() as session:
            print("✓ Database session created successfully")
        
        return True
    except Exception as e:
        print(f"✗ Database manager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Testing Analytics Session Management Fix")
    print("=" * 50)
    
    # Setup logging to capture warnings
    logging.basicConfig(level=logging.WARNING)
    
    tests = [
        test_analytics_import,
        test_analytics_disabled,
        test_database_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Analytics fix appears to be working.")
        return 0
    else:
        print("❌ Some tests failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
