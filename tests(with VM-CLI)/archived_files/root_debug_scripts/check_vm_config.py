#!/usr/bin/env python3
"""
Check VM Configuration

This script shows the current configuration of a VM, including attached
storage devices and ISOs.
"""

import sys
import libvirt
import xml.etree.ElementTree as ET

def check_vm_config(vm_name):
    """Check and display VM configuration"""
    try:
        conn = libvirt.open('qemu:///system')
        if not conn:
            print("❌ Failed to connect to libvirt")
            return False
        
        # Find the VM
        try:
            domain = conn.lookupByName(vm_name)
        except libvirt.libvirtError:
            print(f"❌ VM '{vm_name}' not found")
            conn.close()
            return False
        
        print(f"🔍 VM Configuration: {vm_name}")
        print("=" * 50)
        
        # Basic VM info
        is_active = domain.isActive()
        print(f"Status: {'🟢 Running' if is_active else '🔴 Stopped'}")
        
        if is_active:
            info = domain.info()
            print(f"Memory: {info[1] // 1024} MB")
            print(f"CPU(s): {info[3]}")
        
        # Get VM XML configuration
        xml_desc = domain.XMLDesc(0)
        root = ET.fromstring(xml_desc)
        
        print(f"\n💾 Storage Devices:")
        print("-" * 20)
        
        disk_count = 0
        for disk in root.findall('.//devices/disk'):
            disk_count += 1
            device_type = disk.get('device', 'unknown')
            disk_type = disk.get('type', 'unknown')
            
            # Get target device
            target = disk.find('target')
            target_dev = target.get('dev') if target is not None else 'unknown'
            target_bus = target.get('bus') if target is not None else 'unknown'
            
            # Get source file
            source = disk.find('source')
            source_file = source.get('file') if source is not None else 'none'
            
            # Check if it's readonly (CD/DVD)
            readonly = disk.find('readonly') is not None
            
            print(f"\n  Device {disk_count}:")
            print(f"    Type: {device_type} ({'CD/DVD' if device_type == 'cdrom' else 'Disk'})")
            print(f"    Target: {target_dev} ({target_bus} bus)")
            print(f"    Source: {source_file}")
            print(f"    Read-only: {'Yes' if readonly else 'No'}")
            
            # If it's a file, check if it exists and get size
            if source_file and source_file != 'none':
                import os
                if os.path.exists(source_file):
                    size_bytes = os.path.getsize(source_file)
                    if size_bytes > 1024 * 1024 * 1024:  # GB
                        size_str = f"{size_bytes / (1024**3):.1f} GB"
                    elif size_bytes > 1024 * 1024:  # MB
                        size_str = f"{size_bytes / (1024**2):.1f} MB"
                    else:  # KB
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    print(f"    Size: {size_str}")
                    print(f"    Status: ✅ File exists")
                else:
                    print(f"    Status: ❌ File not found")
        
        if disk_count == 0:
            print("  No storage devices found")
        
        # Network interfaces
        print(f"\n🌐 Network Interfaces:")
        print("-" * 20)
        
        interface_count = 0
        for interface in root.findall('.//devices/interface'):
            interface_count += 1
            interface_type = interface.get('type', 'unknown')
            
            # Get MAC address
            mac = interface.find('mac')
            mac_address = mac.get('address') if mac is not None else 'unknown'
            
            # Get network source
            source = interface.find('source')
            if source is not None:
                network = source.get('network') or source.get('bridge') or 'unknown'
            else:
                network = 'unknown'
            
            print(f"\n  Interface {interface_count}:")
            print(f"    Type: {interface_type}")
            print(f"    MAC: {mac_address}")
            print(f"    Network: {network}")
        
        if interface_count == 0:
            print("  No network interfaces found")
        
        # Boot order
        print(f"\n🚀 Boot Configuration:")
        print("-" * 20)
        
        os_elem = root.find('.//os')
        if os_elem is not None:
            boot_devices = os_elem.findall('boot')
            if boot_devices:
                for i, boot in enumerate(boot_devices, 1):
                    boot_dev = boot.get('dev', 'unknown')
                    print(f"  {i}. {boot_dev}")
            else:
                print("  No specific boot order configured")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking VM configuration: {e}")
        return False

def list_vms():
    """List all available VMs"""
    try:
        conn = libvirt.open('qemu:///system')
        if not conn:
            return []
        
        vms = []
        
        # Active VMs
        active_ids = conn.listDomainsID()
        for domain_id in active_ids:
            try:
                domain = conn.lookupByID(domain_id)
                vms.append((domain.name(), "running"))
            except libvirt.libvirtError:
                continue
        
        # Inactive VMs
        inactive_names = conn.listDefinedDomains()
        for name in inactive_names:
            vms.append((name, "stopped"))
        
        conn.close()
        return vms
        
    except Exception:
        return []

def main():
    """Main function"""
    print("🔍 VM Configuration Checker")
    print("=" * 30)
    
    # Check if VM name was provided as argument
    if len(sys.argv) > 1:
        vm_name = sys.argv[1]
        check_vm_config(vm_name)
        return
    
    # List available VMs
    vms = list_vms()
    if not vms:
        print("❌ No VMs found")
        return
    
    print("\nAvailable VMs:")
    for i, (name, status) in enumerate(vms, 1):
        status_icon = "🟢" if status == "running" else "🔴"
        print(f"  {i}. {name} ({status_icon} {status})")
    
    # Get VM selection
    while True:
        try:
            choice = input(f"\nSelect a VM to check (1-{len(vms)}): ")
            vm_index = int(choice) - 1
            if 0 <= vm_index < len(vms):
                selected_vm = vms[vm_index][0]
                break
            else:
                print("❌ Invalid selection")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Cancelled")
            return
    
    print()  # Empty line
    check_vm_config(selected_vm)

if __name__ == "__main__":
    main()
