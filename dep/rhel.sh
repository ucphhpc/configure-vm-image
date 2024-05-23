#!/bin/bash

# The cloud-localds is used to generate the configuration image
# for cloud-init
dnf install -y cloud-utils --enablerepo devel

# The emulator used to start and configure the image
dnf install -y qemu-kvm

# If the link is missing
ln -s /usr/libexec/qemu-kvm /usr/bin/qemu-kvm

# Used to reset the image before it is deployed
dnf install -y /usr/bin/virt-sysprep
