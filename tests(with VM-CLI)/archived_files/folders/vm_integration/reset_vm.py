#!/usr/bin/env python3
"""
Reset VM to clean base image state
"""

import sys
from pathlib import Path
import libvirt
import xml.etree.ElementTree as ET

def reset_vm_disk(vm_name="ubuntu24.04-2"):
    """Reset VM disk to clean base image."""
    try:
        # Connect to libvirt
        conn = libvirt.open('qemu:///system')
        if not conn:
            print("Failed to connect to libvirt")
            return False
        
        # Find the VM
        try:
            domain = conn.lookupByName(vm_name)
        except libvirt.libvirtError:
            print(f"VM '{vm_name}' not found")
            return False
        
        # Stop VM if running
        if domain.isActive():
            print(f"Stopping VM '{vm_name}'...")
            domain.destroy()
        
        # Get current XML configuration
        xml_desc = domain.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        tree = ET.fromstring(xml_desc)
        
        # Find and fix disk configuration
        images_dir = Path("/var/lib/libvirt/images")
        fixed = False
        
        for device in tree.findall('.//devices/disk[@type="file"][@device="disk"]'):
            source = device.find('source')
            if source is not None and 'file' in source.attrib:
                current_file = source.get('file')
                print(f"Current disk file: {current_file}")
                
                # Look for the original base image
                current_path = Path(current_file)
                vm_base_name = vm_name.replace('.', '')
                
                # Try to find the original base image
                possible_bases = [
                    images_dir / f"{vm_name}.qcow2",
                    images_dir / f"{vm_base_name}.qcow2",
                    images_dir / f"ubuntu2404-2.qcow2",
                    images_dir / f"ubuntu-24.04.qcow2",
                ]
                
                base_image = None
                for candidate in possible_bases:
                    if candidate.exists():
                        print(f"Found potential base image: {candidate}")
                        base_image = candidate
                        break
                
                if not base_image:
                    # List available images for user to choose
                    available_images = list(images_dir.glob("*.qcow2"))
                    available_images = [img for img in available_images if "snap" not in img.name.lower() and "practice" not in img.name.lower()]
                    
                    if available_images:
                        print("\nAvailable base images:")
                        for i, img in enumerate(available_images):
                            print(f"  {i+1}. {img.name}")
                        
                        try:
                            choice = input(f"\nSelect base image for {vm_name} (1-{len(available_images)}, or 'q' to quit): ")
                            if choice.lower() == 'q':
                                return False
                            idx = int(choice) - 1
                            if 0 <= idx < len(available_images):
                                base_image = available_images[idx]
                        except (ValueError, IndexError):
                            print("Invalid selection")
                            return False
                
                if base_image:
                    # Update the disk source
                    source.set('file', str(base_image))
                    print(f"Updated disk source to: {base_image}")
                    fixed = True
        
        if fixed:
            # Update the VM configuration
            new_xml = ET.tostring(tree, encoding='unicode')
            
            # Undefine and redefine the VM
            domain.undefine()
            new_domain = conn.defineXML(new_xml)
            
            print(f"VM '{vm_name}' configuration updated successfully")
            return True
        else:
            print("No disk configuration changes needed")
            return True
            
    except Exception as e:
        print(f"Error resetting VM: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    vm_name = sys.argv[1] if len(sys.argv) > 1 else "ubuntu24.04-2"
    if reset_vm_disk(vm_name):
        print(f"\nVM '{vm_name}' reset successfully!")
        print("You can now run challenges again.")
    else:
        print(f"\nFailed to reset VM '{vm_name}'")
