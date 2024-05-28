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

    usage: configure_image.py [-h] [--image-input-path IMAGE_INPUT_PATH]
                                   [---image-qemu-socket-path IMAGE_QEMU_SOCKET_PATH]
                                   [--config-user-data-path CONFIG_USER_DATA_PATH]
                                   [--config-meta-data-path CONFIG_META_DATA_PATH]
                                   [--config-vendor-data-path CONFIG_VENDOR_DATA_PATH]
                                   [--config-seed-output-path CONFIG_SEED_OUTPUT_PATH]
                                   [--qemu-cpu-model QEMU_CPU_MODEL]

    options:
    -h, --help            show this help message and exit
    --image-input-path IMAGE_INPUT_PATH
                            The path to the image that is to be configured (default: configure-images/image.qcow2)
    ---image-qemu-socket-path IMAGE_QEMU_SOCKET_PATH
                            The path to where the QEMU monitor socket should be placed
                            which is used to send commands to the running image while it is being configured. (default: configure-images/qemu-monitor-socket)
    --config-user-data-path CONFIG_USER_DATA_PATH
                            The path to the cloud-init user-data configuration file (default: cloud-init-config/user-data)
    --config-meta-data-path CONFIG_META_DATA_PATH
                            The path to the cloud-init meta-data configuration file (default: cloud-init-config/meta-data)
    --config-vendor-data-path CONFIG_VENDOR_DATA_PATH
                            The path to the cloud-init vendor-data configuration file (default: cloud-init-config/vendor-data)
    --config-seed-output-path CONFIG_SEED_OUTPUT_PATH
                            The path to the cloud-init output seed image file that is generated based 
                            on the data defined in the user-data, meta-data, and vendor-data configs (default: image-config/seed.img)
    --qemu-cpu-model QEMU_CPU_MODEL
                            The default cpu model for configuring the image (default: host)

To configure the image, the ``configure-vm-image`` tool starts an instance of the image and sends commands to the running image via the QEMU monitor socket.
The configuration files for cloud-init should be defined beforehand and the tool requires that the to be configured image supports cloud-init.

To configure an existing image disk with the default values, ``make configure`` can be run in the root directory of the project::

    make configure ARGS="--image-input-path configure-image/image-to-be-configuerd.qcow2"
