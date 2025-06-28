#!/usr/bin/env python3
"""
Clean up excessively long snapshot filenames
"""

import os
import re
from pathlib import Path

def cleanup_long_snapshots():
    """Clean up snapshot files with excessively long names."""
    snapshot_dir = Path("/var/lib/libvirt/images")
    
    if not snapshot_dir.exists():
        print("Libvirt images directory not found")
        return
    
    # Find files with very long names (>100 characters)
    long_files = []
    for file_path in snapshot_dir.glob("*.qcow2"):
        if len(file_path.name) > 100:
            long_files.append(file_path)
    
    if not long_files:
        print("No excessively long snapshot files found")
        return
    
    print(f"Found {len(long_files)} files with long names:")
    for file_path in long_files:
        print(f"  {file_path.name}")
        
        # Extract base VM name
        name_parts = file_path.stem.split('-')
        base_name = name_parts[0] if name_parts else "unknown"
        
        # Create a shorter name
        import time
        timestamp = int(time.time())
        new_name = f"{base_name}-cleanup-{timestamp}.qcow2"
        new_path = file_path.parent / new_name
        
        try:
            # Rename the file
            os.rename(file_path, new_path)
            print(f"    → Renamed to: {new_name}")
        except OSError as e:
            print(f"    → Error renaming: {e}")
            # If renaming fails, try to delete if it's clearly a snapshot
            if "practice" in file_path.name.lower() or "snapshot" in file_path.name.lower():
                try:
                    file_path.unlink()
                    print(f"    → Deleted problematic snapshot file")
                except OSError:
                    print(f"    → Could not delete file")

if __name__ == "__main__":
    cleanup_long_snapshots()
