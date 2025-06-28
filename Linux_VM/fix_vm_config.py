#!/usr/bin/env python3
"""
Fix VM configuration with correct base image path
"""

import libvirt
import xml.etree.ElementTree as ET
from pathlib import Path

def fix_vm_config(vm_name="ubuntu24.04-2"):
    """Fix VM configuration with actual base image."""
    try:
        # Connect to libvirt
        conn = libvirt.open('qemu:///system')
        if not conn:
            print("Failed to connect to libvirt")
            return False
        
        # Find the VM
        domain = conn.lookupByName(vm_name)
        
        # Stop VM if running
        if domain.isActive():
            print(f"Stopping VM '{vm_name}'...")
            domain.destroy()
        
        # List available images
        images_dir = Path("/var/lib/libvirt/images")
        print(f"\nAvailable disk images in {images_dir}:")
        
        available_images = []
        for img_file in images_dir.glob("*.qcow2"):
            # Skip snapshot files
            if any(skip in img_file.name.lower() for skip in ['snap', 'practice', 'session']):
                continue
            available_images.append(img_file)
            print(f"  {len(available_images)}. {img_file.name}")
        
        if not available_images:
            print("No suitable base images found!")
            return False
        
        # Auto-select if there's an obvious match
        best_match = None
        for img in available_images:
            if vm_name.replace('.', '').replace('-', '') in img.name.replace('.', '').replace('-', ''):
                best_match = img
                break
        
        if best_match:
            selected_image = best_match
            print(f"\nAuto-selected: {selected_image.name}")
        else:
            # Ask user to select
            while True:
                try:
                    choice = input(f"\nSelect base image for {vm_name} (1-{len(available_images)}): ")
                    idx = int(choice) - 1
                    if 0 <= idx < len(available_images):
                        selected_image = available_images[idx]
                        break
                    else:
                        print("Invalid selection")
                except ValueError:
                    print("Please enter a number")
        
        # Get and fix XML configuration
        xml_desc = domain.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        tree = ET.fromstring(xml_desc)
        
        # Find and fix disk sources
        fixed = False
        for device in tree.findall('.//devices/disk[@type="file"][@device="disk"]'):
            source = device.find('source')
            if source is not None and 'file' in source.attrib:
                current_file = source.get('file')
                print(f"\nCurrent disk source: {current_file}")
                
                # Update to correct image
                source.set('file', str(selected_image))
                print(f"Updated to: {selected_image}")
                fixed = True
        
        if fixed:
            # Update VM configuration
            new_xml = ET.tostring(tree, encoding='unicode')
            
            # Undefine and redefine
            domain.undefine()
            conn.defineXML(new_xml)
            
            print(f"\n✅ VM '{vm_name}' configuration fixed!")
            print(f"Base image: {selected_image.name}")
            return True
        else:
            print("No disk configuration found to fix")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if fix_vm_config():
        print("\nVM is ready for challenges!")
    else:
        print("\nFailed to fix VM configuration")
