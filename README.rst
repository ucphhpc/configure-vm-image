==================
configure-vm-image
==================

This package can be used for configuring virtual machine images.

------------
Dependencies
------------

The dependencies required to use this package to generate virtual machine images
can be found in the `dep` directory for the supported distributions.

-----
Setup
-----

The ``qemu-kvm`` command might not be available in the default PATH.
This can be determined via the ``which`` command::

    which qemu-kvm

If the command is not available, the qemu-kvm might be in a different location that is not part of
your current PATH. In this case, you can create a symbolic link to the qemu-kvm command in a directory
An example of this could be::

    ln -s /usr/share/bash-completion/completions/qemu-kvm /usr/local/bin/qemu-kvm

The ``configure-vm-image`` command can be used to generate virtual machine images for the supported distributions.

---------------------------------
Configure a Virtual Machine Image
---------------------------------

To configure a built VM image disk, the ``configure-vm-image`` command can be used.
This tool uses cloud-init to configure the image, and the configuration files for cloud-init should be defined beforehand.
Therefore, the tool requires that the to be configured image supports cloud-init, a list of various distributions cloud-init images can be found below.

- `Rocky <https://download.rockylinux.org/pub/rocky/>`_
- `Debian <https://cloud.debian.org/images/cloud/>`_
- `Ubuntu <https://cloud-images.ubuntu.com/>`_
- `Fedora <https://mirrors.dotsrc.org/fedora-enchilada/linux/releases/39/Cloud/>`_


The default location from where these are expected to be found can be discovered by running the command with the ``--help`` flag::

    usage: configure_image.py [-h] [--config-user-data-path CONFIG_USER_DATA_PATH]
                                   [--config-meta-data-path CONFIG_META_DATA_PATH]
                                   [--config-vendor-data-path CONFIG_VENDOR_DATA_PATH]
                                   [--config-network-config-path CONFIG_NETWORK_CONFIG_PATH]
                                   [--staging-image-path STAGING_IMAGE_PATH]
                                   [--staging-socket-path STAGING_SOCKET_PATH]
                                   [--qemu-cpu-model QEMU_CPU_MODEL]
                                   image_path

    positional arguments:
    image_path            The path to the image that is to be configured

    options:
    -h, --help            show this help message and exit
    --config-user-data-path CONFIG_USER_DATA_PATH
                            The path to the cloud-init user-data configuration file (default: cloud-init/user-data)
    --config-meta-data-path CONFIG_META_DATA_PATH
                            The path to the cloud-init meta-data configuration file (default: cloud-init/meta-data)
    --config-vendor-data-path CONFIG_VENDOR_DATA_PATH
                            The path to the cloud-init vendor-data configuration file (default: cloud-init/vendor-data)
    --config-network-config-path CONFIG_NETWORK_CONFIG_PATH
                            The path to the cloud-init network-config configuration file that is used to configure the network settings of the image (default: cloud-init/network-config)
    --staging-image-path STAGING_IMAGE_PATH
                            The path to the cloud-init output seed image file that is generated based on the data defined in the user-data, meta-data, vendor-data, and network-config files. This seed image file is then subsequently used to configure the defined input image. (default:
                            /tmp/configure-vm-image/seed.img)
    --staging-socket-path STAGING_SOCKET_PATH
                            The path to where the QEMU monitor socket should be placed which is used to send commands to the running image while it is being configured. (default: /tmp/configure-vm-image/qemu-monitor-socket)
    --qemu-cpu-model QEMU_CPU_MODEL
                            The default cpu model for configuring the image (default: host)

To configure the image, the ``configure-vm-image`` tool creates a seed disk image with the cloud-init configuration and subsequently starts the ``image_path`` with the mounted seed image.
This process then runs until the cloud-init configuration is complete and the image is shut down.

The configuration files for cloud-init should be defined beforehand and the tool requires that the to-be-configured image supports cloud-init.