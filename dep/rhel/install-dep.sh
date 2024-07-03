#!/bin/bash

# genisoimage is required to create the cloud-init ISO image that is used
# to configure the VM on first boot
dnf install -y genisoimage

# Used to reset the image before it is deployed
dnf install -y /usr/bin/virt-sysprep
