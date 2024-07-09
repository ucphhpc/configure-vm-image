==================
configure-vm-image
==================

.. image:: https://img.shields.io/pypi/pyversions/configure-vm-image.svg
    :target: https://img.shields.io/pypi/pyversions/configure-vm-image
.. image:: https://badge.fury.io/py/configure-vm-image.svg
    :target: https://badge.fury.io/py/configure-vm-image

This package can be used for configuring existing virtual machine images.
Virtual machine images can be either downloaded straight from a distribution provider (see cloud_init_images_) or generated via tools such as the `gen-vm-image <https://github.com/ucphhpc/gen-vm-image>`_.

------------
Dependencies
------------

The following dependencies are required to be installed on the system to use the ``configure-vm-image`` command:

    - `genisoimage <https://linux.die.net/man/1/genisoimage>`_
    - `virt-sysprep <https://linux.die.net/man/1/virt-sysprep>`_

How to install each of these for a given distribution can be found at `pkgs.org <https://pkgs.org/>`_.
Dependency install scripts for various distributions can be found in the ``dep`` root directory of this package.

-------
Install
-------

The tool itself can be installed either via pip::

    pip install configure-vm-image

or by cloning the repository and running the following command in the root directory::

    make install

If no argument is given to the ``make install`` command, the package will be installed inside a virtual environment called ``venv`` in the root directory of the package.
The ``VENV_NAME`` argument can be used to specify a different name for the virtual environment inwhich the package is installed.

-----
Usage
-----

Upon installation, the ``configure-vm-image`` command is installed and can be used to configure an existing virtual machine image.
To generate such an image, the `gen-vm-image <https://github.com/ucphhpc/gen-vm-image>`_ tool is available.

To configure the existing image itself, ``configure-vm-image`` uses the `cloud-init <https://cloudinit.readthedocs.io/en/latest/index.html>`_ tool to customize the image.
`cloud-init <https://cloudinit.readthedocs.io/en/latest/index.html>`_ itself achives this by running a set of scripts upon image boot that utilises a set of preset configuration files.
These configuration files includes::

    - user-data
    - meta-data
    - vendor-data
    - network-config

.. _help_output:

Therefore, the ``configure-vm-image`` tool attempts to load each of these files when launched from the given parameter set paths for each of them.
The parameter names for these can be discovered by running the command with the ``--help`` flag::

    usage: configure_image.py [-h]
                              [--image-format IMAGE_FORMAT]
                              [--config-user-data-path CONFIG_USER_DATA_PATH]
                              [--config-meta-data-path CONFIG_META_DATA_PATH]
                              [--config-vendor-data-path CONFIG_VENDOR_DATA_PATH]
                              [--config-network-config-path CONFIG_NETWORK_CONFIG_PATH]
                              [--configure-vm-name CONFIGURE_VM_NAME]
                              [--configure-vm-cpu-model CONFIGURE_VM_CPU_MODEL]
                              [--configure-vm-vcpus CONFIGURE_VM_VCPUS]
                              [--configure-vm-memory CONFIGURE_VM_MEMORY]
                              [--cloud-init-iso-output-path CLOUD_INIT_ISO_OUTPUT_PATH]
                              [--configure-vm-log-path CONFIGURE_VM_LOG_PATH]
                              [--configure-vm-template-path CONFIGURE_VM_TEMPLATE_PATH]
                              [--configure-vm-template-values KEY=VALUE [KEY=VALUE ...]]
                              [--reset-operations RESET_OPERATIONS]
                              [--verbose]
                              image_path

    positional arguments:
    image_path            The path to the image that is to be configured.

    options:
    -h, --help            show this help message and exit
    --image-format IMAGE_FORMAT
                            The format of the image that is to be configured. 
                            The tool tries to automatically discover this if not set. (default: None)
    --config-user-data-path CONFIG_USER_DATA_PATH
                            The path to the cloud-init user-data configuration file. (default: cloud-init/user-data)
    --config-meta-data-path CONFIG_META_DATA_PATH
                            The path to the cloud-init meta-data configuration file. (default: cloud-init/meta-data)
    --config-vendor-data-path CONFIG_VENDOR_DATA_PATH
                            The path to the cloud-init vendor-data configuration file. (default: cloud-init/vendor-data)
    --config-network-config-path CONFIG_NETWORK_CONFIG_PATH
                            The path to the cloud-init network-config configuration file that is used to configure the network settings of the image.
                            (default: cloud-init/network-config)
    --configure-vm-name CONFIGURE_VM_NAME, -n CONFIGURE_VM_NAME
                            The name of the VM that is used to configure the image. (default: configure-vm-image)
    --configure-vm-cpu-model CONFIGURE_VM_CPU_MODEL, -cv-cpu CONFIGURE_VM_CPU_MODEL
                            The cpu model to use for virtualization when configuring the image. (default: None)
    --configure-vm-vcpus CONFIGURE_VM_VCPUS, -cv-vcpus CONFIGURE_VM_VCPUS
                            The number of virtual CPUs to allocate to the VM when configuring the image. (default: 1)
    --configure-vm-memory CONFIGURE_VM_MEMORY, -cv-m CONFIGURE_VM_MEMORY
                            The amount of memory to allocate to the VM when configuring the image. (default: 2048MiB)
    --cloud-init-iso-output-path CLOUD_INIT_ISO_OUTPUT_PATH, -ci-output CLOUD_INIT_ISO_OUTPUT_PATH
                            The path to the cloud-init output ISO image file that is generated based 
                            on the data defined in the user-data, meta-data, vendor-data, and network-config files.
                            This seed ISO is then subsequently used to configure the defined input image. (default: cloud-init/cidata.iso)
    --configure-vm-log-path CONFIGURE_VM_LOG_PATH, -cv-log CONFIGURE_VM_LOG_PATH
                            The path to the log file that is used to log the output of the configuring VM. (default: tmp/configure-vm.log)
    --configure-vm-template-path CONFIGURE_VM_TEMPLATE_PATH
                            The path to the template file that is used to configure the VM. (default: res/configure-vm-template.xml.j2)
    --configure-vm-template-values KEY=VALUE [KEY=VALUE ...], -tv KEY=VALUE [KEY=VALUE ...]
                            An additional set of key=value pair arguments that should be passed to the --configure-vm-template.
                            If a value contains spaces, you should define it with quotes. (default: [])
    --reset-operations RESET_OPERATIONS
                            The operations to perform during the reset operation. (default: defaults,-ssh-userdir)
    --verbose, -v         Flag to enable verbose output (default: False)

As can be gathered from the help output, ``configure-vm-image`` expects that each of these `cloud-init <https://cloudinit.readthedocs.io/en/latest/index.html>`_ configuration files are present in a ``cloud-init`` directory in the current path when ``configure-vm-image`` is executed.
If any of these configuration files are not present, the tool will skip that particular configuration file and continue on even if none are given.
This means that the tool can be used to configure an image with only a subset of the configuration files or none at all.

.. _cloud_init_images:

-----------------
Cloud-init Images
-----------------

Most distributions have a publically available cloud-init image that can be downloaded. A subset highlight of these can be found below.

- `Rocky <https://download.rockylinux.org/pub/rocky/>`_
- `Debian <https://cloud.debian.org/images/cloud/>`_
- `Ubuntu <https://cloud-images.ubuntu.com/>`_
- `Fedora <https://mirrors.dotsrc.org/fedora-enchilada/linux/releases/39/Cloud/>`_

-------------
Basic Example
-------------

In this example, we will configure an existing virtual machine image with a basic cloud-init configuration.
This includes creating a ``default_user`` with sudo capabilities that can authenticate via the console with a password.
An example of such configuration can be found in the ``examples/basic-cloud-init`` directory of this package.
To use this, we can create a symlink of it in the root directory of the repo::

    ln -s examples/basic-cloud-init cloud-init

Subsequently, you can adjust the configuration files to your liking and in accordance with the `cloud-init <https://cloudinit.readthedocs.io/en/latest/index.html>`_ documentation.

After this has been prepared, 
But, before we can begin, we need to install the dependencies for the tool::
    
    ./dep/<distro>/install-dep.sh

With this in place, we can now configure the image by running the following command::

    configure-vm-image <path_to_image>

This will both generate a cloud-init ISO image and launch a virtual machine that mounts said ISO and the disk image to be configured.
Upon launch, the output of the configuring VM will be logged to the log file specified with the ``--configure-vm-log-path`` parameter,
which default can be seen in the ``help`` output above in help_output_. Additional output from the ``configure-vm-image`` tool can also be produced with the ``--verbose`` flag
as also highlighted in the help output.


------------------------
Additional Disks Example
------------------------

Beyond the simple example, where a single disk image is configured, ``configure-vm-image`` can also be used to partition and format additional disks beyond the primary vm image disk.
This can be achived by using the ``cloud-init`` feature of `disk_setup <https://cloudinit.readthedocs.io/en/latest/reference/modules.html#disk-setup>`_ and `fs_setup <https://cloudinit.readthedocs.io/en/latest/reference/modules.html#disk-setup>`_.
An example of such a cloud-init configuration can be found in the ``examples/disk-setup-cloud-init`` directory of this package.
In the example, three additional disks are expected to be present in the VM at the specified device paths, namely:

    - /dev/vdb
    - /dev/vdc
    - /dev/vdd

To ensure this, the VM template file (as specified with ``--configure-vm-template``) should be adjusted to include these disks::

    <devices>
    ...
    <disk type='file' device='disk'>
        <driver name='qemu' type='raw'/>
        <source file='{{disk2_path}}'/>
        <target dev='vdb' bus='virtio'/>
    </disk>
    <disk type='file' device='disk'>
        <driver name='qemu' type='raw'/>
        <source file='{{disk3_path}}'/>
        <target dev='vdc' bus='virtio'/>
    </disk>
    <disk type='file' device='disk'>
        <driver name='qemu' type='raw'/>
        <source file='{{disk4_path}}'/>
        <target dev='vdd' bus='virtio'/>
    </disk>
    ...
    </devices>

Here it is important to match the target device names with the device paths specified in the cloud-init configuration file.
After this has been prepared, the cloud-init configuration files can be symlinked to the root directory of the repo::

    ln -s examples/disk-setup-cloud-init cloud-init

Once this is complete, the ``configure-vm-image`` tool can be run with the nessesary template values that specify the paths to the additional disk images::

    configure-vm-image <path_to_image> --configure-vm-template-values disk2_path=<path_to_disk2> disk3_path=<path_to_disk3> disk4_path=<path_to_disk4>

This will configure the image with the additional disks as specified in the cloud-init configuration file.
