import os
from configure_vm_image.common.defaults import CLOUD_INIT_DIR, TMP_DIR, RES_DIR


def configure_group(parser):
    configure_group_ = parser.add_argument_group(
        title="Configure Virtual Machine Image"
    )
    configure_group_.add_argument(
        "image_path",
        help="The path to the image that is to be configured.",
    )
    configure_group_.add_argument(
        "--image-format",
        default=None,
        help="The format of the image that is to be configured. The tool tries to automatically discover this if not set.",
    )
    configure_group_.add_argument(
        "--config-user-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "user-data"),
        help="The path to the cloud-init user-data configuration file.",
    )
    configure_group_.add_argument(
        "--config-meta-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "meta-data"),
        help="The path to the cloud-init meta-data configuration file.",
    )
    configure_group_.add_argument(
        "--config-vendor-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "vendor-data"),
        help="The path to the cloud-init vendor-data configuration file.",
    )
    configure_group_.add_argument(
        "--config-network-config-path",
        default=os.path.join(CLOUD_INIT_DIR, "network-config"),
        help="""The path to the cloud-init network-config configuration file
        that is used to configure the network settings of the image.""",
    )
    configure_group_.add_argument(
        "--configure-vm-orchestrator",
        "-cv-orch",
        default="libvirt-provider",
        help="The orchestrator to use when provisioning the virtual machine that is used to configure a particular virtual machine image",
    )
    configure_group_.add_argument(
        "--configure-vm-name",
        "-cv-name",
        default="configure-vm-image",
        help="The name of the VM that is used to configure the image.",
    )
    configure_group_.add_argument(
        "--cloud-init-iso-output-path",
        "-ci-output",
        default=os.path.join(CLOUD_INIT_DIR, "cidata.iso"),
        help="""The path to the cloud-init output iso image file that is generated
        based on the data defined in the user-data, meta-data, vendor-data, and network-config files.
        This seed iso file is then subsequently used to configure the defined input image.""",
    )
    configure_group_.add_argument(
        "--configure-vm-log-path",
        "-cv-log",
        default=os.path.join(TMP_DIR, "configure-vm.log"),
        help="""The path to the log file that is used to log the output of the configuring VM.""",
    )
    configure_group_.add_argument(
        "--configure-vm-template-path",
        default=os.path.join(RES_DIR, "configure-vm-template.xml.j2"),
        help="""The path to the template file that is used to configure the VM.""",
    )
    configure_group_.add_argument(
        "--configure-vm-template-values",
        "-tv",
        metavar="KEY=VALUE",
        nargs="+",
        default=[],
        help="""An additional set of key=value pair arguments that should be passed to the --configure-vm-template.
        If a value contains spaces, you should define it with quotes.
        """,
    )
    configure_group_.add_argument(
        "--reset-operations",
        default="defaults,-ssh-userdir",
        help="""The operations to perform during the reset operation.""",
    )
    configure_group_.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Flag to enable verbose output.",
    )
    configure_group_.add_argument(
        "--verbose-reset",
        "-vr",
        action="store_true",
        default=False,
        help="Flag to enable verbose output during the reset.",
    )
