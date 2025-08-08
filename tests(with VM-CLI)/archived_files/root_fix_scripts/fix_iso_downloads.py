#!/usr/bin/env python3
"""
Fix ISO Download Configuration

This script fixes the web settings to enable ISO downloads with proper URLs
and configure the correct download path.
"""

import json
import os
from pathlib import Path

def fix_iso_downloads():
    """Fix the ISO download configuration in web_settings.json"""
    
    # Path to the web settings file
    settings_file = Path(__file__).parent / "web_settings.json"
    
    # Load current settings
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    else:
        settings = {}
    
    print("Current ISO settings:")
    iso_settings = settings.get('isoDownloads', {})
    print(f"  Enabled: {iso_settings.get('enabled', False)}")
    print(f"  Download Path: {iso_settings.get('downloadPath', 'Not set')}")
    print(f"  URLs configured: {len(iso_settings.get('urls', {}))}")
    
    # Define proper ISO download URLs for common Linux distributions
    iso_urls = {
        "ubuntu-22.04": "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso",
        "ubuntu-20.04": "https://releases.ubuntu.com/20.04/ubuntu-20.04.6-live-server-amd64.iso",
        "debian-12": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.2.0-amd64-netinst.iso",
        "debian-11": "https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/debian-live-11.8.0-amd64-standard.iso",
        "centos-stream-9": "https://mirror.stream.centos.org/9-stream/BaseOS/x86_64/iso/CentOS-Stream-9-latest-x86_64-boot.iso",
        "rhel-9": "https://access.redhat.com/downloads/content/479/ver=/rhel---9/9.2/x86_64/product-software",
        "fedora-39": "https://download.fedoraproject.org/pub/fedora/linux/releases/39/Server/x86_64/iso/Fedora-Server-netinst-x86_64-39-1.5.iso",
        "fedora-38": "https://download.fedoraproject.org/pub/fedora/linux/releases/38/Server/x86_64/iso/Fedora-Server-netinst-x86_64-38-1.6.iso",
        "arch-linux": "https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso",
        "alpine-linux": "https://dl-cdn.alpinelinux.org/alpine/v3.18/releases/x86_64/alpine-standard-3.18.4-x86_64.iso"
    }
    
    # Set up the vm-storage directory
    vm_storage_path = str(Path.home() / "vm-storage" / "isos")
    os.makedirs(vm_storage_path, exist_ok=True)
    
    # Update settings
    settings['isoDownloads'] = {
        "enabled": True,
        "downloadPath": vm_storage_path,
        "urls": iso_urls
    }
    
    # Also update VM defaults to enable auto-download
    if 'vmDefaults' not in settings:
        settings['vmDefaults'] = {}
    
    settings['vmDefaults']['autoDownloadIso'] = True
    
    # Save the updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print("\n✅ Fixed ISO download configuration:")
    print(f"  ✓ ISO downloads enabled")
    print(f"  ✓ Download path set to: {vm_storage_path}")
    print(f"  ✓ Configured {len(iso_urls)} ISO URLs")
    print(f"  ✓ Auto-download enabled by default")
    
    print(f"\nConfigured distributions:")
    for template, url in iso_urls.items():
        print(f"  • {template}")
    
    print(f"\nISO files will be downloaded to: {vm_storage_path}")
    print(f"Existing ISO files:")
    
    # List existing ISO files
    iso_path = Path(vm_storage_path)
    if iso_path.exists():
        iso_files = list(iso_path.glob("*.iso"))
        if iso_files:
            for iso_file in iso_files:
                size_mb = iso_file.stat().st_size / (1024 * 1024)
                print(f"  • {iso_file.name} ({size_mb:.1f} MB)")
        else:
            print("  (none found)")
    else:
        print("  (directory doesn't exist yet)")

def test_iso_download():
    """Test the ISO download functionality"""
    print("\n" + "="*50)
    print("Testing ISO Download Functionality")
    print("="*50)
    
    try:
        # Import the web view to test the _handle_iso_download method
        import sys
        sys.path.append(str(Path(__file__).parent))
        
        from views.web_view import LinuxPlusStudyWeb
        
        # Create a minimal web app instance
        web_app = LinuxPlusStudyWeb(None, None, None)
        
        # Test downloading an Ubuntu ISO (if it doesn't exist)
        print("\nTesting Ubuntu 22.04 ISO download...")
        iso_path = web_app._handle_iso_download("ubuntu-22.04")
        
        if iso_path and os.path.exists(iso_path):
            size_mb = os.path.getsize(iso_path) / (1024 * 1024)
            print(f"✅ ISO available at: {iso_path}")
            print(f"   Size: {size_mb:.1f} MB")
        else:
            print("❌ ISO download failed or file not found")
            
    except Exception as e:
        print(f"❌ Error testing ISO download: {e}")

if __name__ == "__main__":
    print("🔧 Fixing ISO Download Configuration")
    print("="*50)
    
    fix_iso_downloads()
    
    # Optionally test the download (commented out to avoid long download)
    # test_iso_download()
    
    print(f"\n🎉 Configuration fixed! You can now create VMs with automatic ISO downloads.")
    print(f"\nTo create a VM with ISO download:")
    print(f"1. Go to the VM Playground in the web interface")
    print(f"2. Click 'Create VM'")
    print(f"3. Make sure 'Download ISO automatically' is checked")
    print(f"4. Select your preferred Linux distribution")
    print(f"5. Click 'Create VM'")
