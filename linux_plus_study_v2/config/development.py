"""Configuration for development environment."""

import os

class DevelopmentConfig:
    """Development environment configuration."""
    
    # Database
    DATABASE_URL = "sqlite:///data/linux_plus_study.db"
    
    # Debug settings
    DEBUG = True
    TESTING = False
    
    # VM Storage paths (excluded from Git)
    VM_STORAGE_BASE = os.path.expanduser("~/vm-storage")
    ISO_STORAGE_PATH = os.path.join(VM_STORAGE_BASE, "isos")
    VM_IMAGES_PATH = os.path.join(VM_STORAGE_BASE, "vms")
    SNAPSHOTS_PATH = os.path.join(VM_STORAGE_BASE, "snapshots")
    
    # Logging
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "logs/linux_plus_study.log"
    
    # Security (development only)
    SECRET_KEY = "dev-secret-key-change-in-production"
    
    # VM Integration
    VM_ENABLED = True
    MAX_CONCURRENT_VMS = 3
    VM_MEMORY_LIMIT_MB = 2048
    
    # Practice settings
    PRACTICE_SESSION_TIMEOUT = 3600  # 1 hour
    AUTO_SAVE_INTERVAL = 300  # 5 minutes