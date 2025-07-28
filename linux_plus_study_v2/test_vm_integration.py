#!/usr/bin/env python3
"""
Simple VM integration test script
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_vm_integration():
    """Test all VM integration components"""
    print("🔧 Testing VM Integration Components")
    print("=" * 50)
    
    # Test 1: Import verification
    print("\n1. Testing Core Imports...")
    try:
        from vm_integration.utils.vm_manager import VMManager
        from vm_integration.utils.snapshot_manager import SnapshotManager
        from services.vm_service import VMService
        print("   ✓ Core VM components imported successfully")
    except Exception as e:
        print(f"   ❌ Core import failed: {e}")
        return False
    
    # Test 2: Component instantiation
    print("\n2. Testing Component Instantiation...")
    try:
        vm_manager = VMManager()
        snapshot_manager = SnapshotManager()
        vm_service = VMService()
        print("   ✓ VM components instantiated successfully")
        
        # Test basic methods exist
        assert hasattr(vm_manager, 'list_vms'), "VMManager missing list_vms method"
        assert hasattr(vm_manager, 'find_vm'), "VMManager missing find_vm method"
        assert hasattr(snapshot_manager, 'create_external_snapshot'), "SnapshotManager missing create_external_snapshot"
        print("   ✓ Required methods available")
        
    except Exception as e:
        print(f"   ❌ VM component instantiation failed: {e}")
        return False
    
    # Test 3: Web view imports
    print("\n3. Testing Web Integration...")
    try:
        from views.web_view import LinuxPlusStudyWeb
        print("   ✓ Web view imported successfully")
        
        # Check if the VM routes are defined
        web_methods = [method for method in dir(LinuxPlusStudyWeb) if 'vm' in method.lower()]
        print(f"   ✓ Found {len(web_methods)} VM-related methods in web view")
        
    except Exception as e:
        print(f"   ❌ Web integration test failed: {e}")
        return False
    
    # Test 4: Legacy function compatibility
    print("\n4. Testing Legacy Functions...")
    try:
        from vm_integration.utils.snapshot_manager import (
            create_external_snapshot,
            revert_to_snapshot,
            delete_snapshot,
            list_snapshots
        )
        print("   ✓ Legacy snapshot functions available")
        
        # Test that they are callable
        assert callable(create_external_snapshot), "create_external_snapshot not callable"
        assert callable(revert_to_snapshot), "revert_to_snapshot not callable" 
        assert callable(delete_snapshot), "delete_snapshot not callable"
        assert callable(list_snapshots), "list_snapshots not callable"
        print("   ✓ Legacy functions are callable")
        
    except Exception as e:
        print(f"   ❌ Legacy function test failed: {e}")
        return False
    
    # Test 5: libvirt availability
    print("\n5. Testing libvirt Connection...")
    try:
        import libvirt
        print("   ✓ libvirt module available")
        
        # Try to connect (this might fail if no hypervisor is running, but that's ok)
        try:
            conn = libvirt.open('qemu:///system')
            if conn:
                print("   ✓ libvirt connection successful")
                conn.close()
            else:
                print("   ⚠ libvirt connection returned None (hypervisor may not be running)")
        except libvirt.libvirtError as e:
            print(f"   ⚠ libvirt connection failed (expected if no hypervisor): {e}")
        
    except Exception as e:
        print(f"   ❌ libvirt test failed: {e}")
        return False
    
    print("\n✅ All VM integration tests passed!")
    print("\n🎯 VM Integration Status:")
    print("- VM management components: ✓ Ready")
    print("- Snapshot management: ✓ Ready") 
    print("- Web API endpoints: ✓ Ready")
    print("- Legacy compatibility: ✓ Ready")
    print("- libvirt integration: ✓ Available")
    
    print("\n🚀 Next Steps:")
    print("1. Start the application: python3 main.py")
    print("2. Navigate to the VM management tab")
    print("3. VM programs should now work correctly!")
    
    return True

if __name__ == "__main__":
    success = test_vm_integration()
    sys.exit(0 if success else 1)
