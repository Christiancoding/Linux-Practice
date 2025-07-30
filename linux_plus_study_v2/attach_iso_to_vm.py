#!/usr/bin/env python3
"""
Attach ISO to Existing VM

This script allows you to attach an ISO file to an existing VM that was
created without one.
"""

import sys
import os
import libvirt
from pathlib import Path

def list_vms():
    """List all available VMs"""
    try:
        conn = libvirt.open('qemu:///system')
        if not conn:
            print("❌ Failed to connect to libvirt")
            return []
        
        # Get all domains (VMs)
        all_domains = []
        
        # Active (running) VMs
        active_ids = conn.listDomainsID()
        for domain_id in active_ids:
            try:
                domain = conn.lookupByID(domain_id)
                all_domains.append((domain.name(), "running"))
            except libvirt.libvirtError:
                continue
        
        # Inactive (stopped) VMs
        inactive_names = conn.listDefinedDomains()
        for name in inactive_names:
            all_domains.append((name, "stopped"))
        
        conn.close()
        return all_domains
        
    except Exception as e:
        print(f"❌ Error listing VMs: {e}")
        return []

def list_isos():
    """List available ISO files"""
    iso_dir = Path.home() / "vm-storage" / "isos"
    if not iso_dir.exists():
        return []
    
    iso_files = list(iso_dir.glob("*.iso"))
    return [(iso.name, str(iso)) for iso in iso_files]

def attach_iso_to_vm(vm_name, iso_path):
    """Attach an ISO file to a VM"""
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
        
        # Check if VM is running (we need to stop it to attach ISO)
        is_active = domain.isActive()
        if is_active:
            print(f"⏸️  Stopping VM '{vm_name}' to attach ISO...")
            domain.destroy()
        
        # Create CDROM device XML
        cdrom_xml = f"""<disk type='file' device='cdrom'>
  <driver name='qemu' type='raw'/>
  <source file='{iso_path}'/>
  <target dev='sda' bus='sata'/>
  <readonly/>
</disk>"""
        
        # Attach the CDROM device
        domain.attachDeviceFlags(cdrom_xml, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        
        print(f"✅ Successfully attached ISO '{iso_path}' to VM '{vm_name}'")
        
        # Restart the VM if it was running
        if is_active:
            print(f"🚀 Starting VM '{vm_name}'...")
            domain.create()
            print(f"✅ VM '{vm_name}' started with ISO attached")
        else:
            print(f"💡 VM '{vm_name}' is ready. Start it to boot from the ISO.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error attaching ISO: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Attach ISO to Existing VM")
    print("=" * 40)
    
    # List available VMs
    vms = list_vms()
    if not vms:
        print("❌ No VMs found. Create a VM first.")
        return
    
    print("\nAvailable VMs:")
    for i, (name, status) in enumerate(vms, 1):
        print(f"  {i}. {name} ({status})")
    
    # Get VM selection
    while True:
        try:
            choice = input(f"\nSelect a VM (1-{len(vms)}): ")
            vm_index = int(choice) - 1
            if 0 <= vm_index < len(vms):
                selected_vm = vms[vm_index][0]
                break
            else:
                print("❌ Invalid selection")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Cancelled")
            return
    
    # List available ISOs
    isos = list_isos()
    if not isos:
        print("❌ No ISO files found in ~/vm-storage/isos/")
        print("💡 Download an ISO file first or run the fix_iso_downloads.py script")
        return
    
    print(f"\nAvailable ISO files:")
    for i, (name, path) in enumerate(isos, 1):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  {i}. {name} ({size_mb:.1f} MB)")
    
    # Get ISO selection
    while True:
        try:
            choice = input(f"\nSelect an ISO (1-{len(isos)}): ")
            iso_index = int(choice) - 1
            if 0 <= iso_index < len(isos):
                selected_iso = isos[iso_index][1]
                break
            else:
                print("❌ Invalid selection")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Cancelled")
            return
    
    # Confirm the operation
    print(f"\n📋 Summary:")
    print(f"  VM: {selected_vm}")
    print(f"  ISO: {os.path.basename(selected_iso)}")
    
    confirm = input("\nProceed? (y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print("👋 Cancelled")
        return
    
    # Attach the ISO
    print(f"\n🔗 Attaching ISO to VM...")
    if attach_iso_to_vm(selected_vm, selected_iso):
        print(f"\n🎉 Success! ISO attached to VM '{selected_vm}'")
        print(f"\n💡 Next steps:")
        print(f"  1. Start the VM if it's not running")
        print(f"  2. The VM will boot from the attached ISO")
        print(f"  3. Follow the OS installation process")
    else:
        print(f"\n❌ Failed to attach ISO to VM")

if __name__ == "__main__":
    main()
