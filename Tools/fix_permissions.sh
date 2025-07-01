#!/bin/bash

echo "Fixing libvirt permissions..."

# Add current user to libvirt group
sudo usermod -a -G libvirt $USER

# Fix ownership of VM images
sudo chown libvirt-qemu:libvirt /var/lib/libvirt/images/*.qcow2 2>/dev/null || true

# Fix permissions of VM images  
sudo chmod 660 /var/lib/libvirt/images/*.qcow2 2>/dev/null || true

# Restart libvirtd service
sudo systemctl restart libvirtd

echo "Permissions fixed. Please log out and back in for group changes to take effect."
echo "Or run: newgrp libvirt"
