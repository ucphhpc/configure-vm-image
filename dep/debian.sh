#!/bin/bash

# genisoimage is required to create the cloud-init ISO image that is used
# to configure the VM on first boot
apt install -y genisoimage

# virt-sysprep is provided by guestfs-tools
apt install -y guestfs-tools