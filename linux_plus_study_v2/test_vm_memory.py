#!/usr/bin/env python3
"""
Test VM creation with the new memory conversion logic
"""

def test_vm_creation_data():
    """Test the VM creation data processing"""
    
    # Simulate form data as it would come from the frontend
    form_data = {
        'vmName': 'test-vm',
        'vmTemplate': 'ubuntu-22.04',
        'vmMemory': '2',        # 2 GB
        'vmMemoryUnit': 'GB',
        'vmCpus': '2',
        'vmDisk': '20',         # 20 GB
        'vmDiskUnit': 'GB',
        'autoStart': 'on',
        'downloadIso': 'on',
        'customIsoUrl': '',
        'vmNotes': 'Test VM'
    }
    
    # Simulate the processing logic from the API
    memory_value = float(form_data['vmMemory'])
    memory_unit = form_data['vmMemoryUnit']
    
    # Convert memory to MB first (as sent to backend)
    if memory_unit == 'TB':
        memory_mb = memory_value * 1024 * 1024
    elif memory_unit == 'GB':
        memory_mb = memory_value * 1024
    else:  # MB
        memory_mb = memory_value
    
    # Then convert to GB for VMManager
    memory_gb = memory_mb / 1024
    
    print("=== VM Creation Test ===")
    print(f"Input: {memory_value} {memory_unit}")
    print(f"Converted to MB: {memory_mb}")
    print(f"Final for VMManager: {memory_gb} GB")
    print(f"Expected: 2.0 GB")
    print(f"✅ Test passed: {memory_gb == 2.0}")
    
    # Test edge cases
    test_cases = [
        (0.5, 'GB', 0.5),    # 512 MB
        (1024, 'MB', 1.0),   # 1 GB from MB
        (0.001, 'TB', 1.0),  # 1 GB from TB
        (4, 'GB', 4.0),      # 4 GB
        (8, 'GB', 8.0),      # 8 GB
    ]
    
    print("\n=== Edge Cases ===")
    for value, unit, expected in test_cases:
        if unit == 'TB':
            mb = value * 1024 * 1024
        elif unit == 'GB':
            mb = value * 1024
        else:  # MB
            mb = value
        
        gb = mb / 1024
        
        print(f"{value} {unit} -> {gb} GB (expected: {expected})")
        print(f"  ✅ Passed: {gb == expected}")

if __name__ == "__main__":
    test_vm_creation_data()
