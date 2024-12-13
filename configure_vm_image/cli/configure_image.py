import argparse
import os
import sys
import json
from configure_vm_image._version import __version__
from configure_vm_image.configure import configure_vm_image
from configure_vm_image.common.utils import to_str, error_print
from configure_vm_image.common.defaults import (
    CLOUD_INIT_DIR,
    PACKAGE_NAME,
    TMP_DIR,
    RES_DIR,
)
from configure_vm_image.common.codes import (
    SUCCESS,
    JSON_DUMP_ERROR,
    JSON_DUMP_ERROR_MSG,
)

SCRIPT_NAME = __file__


def add_build_image_cli_arguments(parser):
    parser.add_argument(
        "image_path",
        help="The path to the image that is to be configured.",
    )
    parser.add_argument(
        "--image-format",
        default=None,
        help="The format of the image that is to be configured. The tool tries to automatically discover this if not set.",
    )
    parser.add_argument(
        "--config-user-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "user-data"),
        help="The path to the cloud-init user-data configuration file.",
    )
    parser.add_argument(
        "--config-meta-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "meta-data"),
        help="The path to the cloud-init meta-data configuration file.",
    )
    parser.add_argument(
        "--config-vendor-data-path",
        default=os.path.join(CLOUD_INIT_DIR, "vendor-data"),
        help="The path to the cloud-init vendor-data configuration file.",
    )
    parser.add_argument(
        "--config-network-config-path",
        default=os.path.join(CLOUD_INIT_DIR, "network-config"),
        help="""The path to the cloud-init network-config configuration file
        that is used to configure the network settings of the image.""",
    )
    parser.add_argument(
        "--configure-vm-name",
        "-n",
        default=PACKAGE_NAME,
        help="""The name of the VM that is used to configure the image.""",
    )
    # https://qemu-project.gitlab.io/qemu/system/qemu-cpu-models.html
    parser.add_argument(
        "--configure-vm-cpu-model",
        "-cv-cpu",
        default=None,
        help="""The cpu model to use for virtualization when configuring the image.""",
    )
    parser.add_argument(
        "--configure-vm-vcpus",
        "-cv-vcpus",
        default="1",
        type=str,
        help="""The number of virtual CPUs to allocate to the VM when configuring the image.""",
    )
    parser.add_argument(
        "--configure-vm-memory",
        "-cv-m",
        default="2048MiB",
        help="""The amount of memory to allocate to the VM when configuring the image.""",
    )
    parser.add_argument(
        "--cloud-init-iso-output-path",
        "-ci-output",
        default=os.path.join(CLOUD_INIT_DIR, "cidata.iso"),
        help="""The path to the cloud-init output iso image file that is generated
        based on the data defined in the user-data, meta-data, vendor-data, and network-config files.
        This seed iso file is then subsequently used to configure the defined input image.""",
    )
    parser.add_argument(
        "--configure-vm-log-path",
        "-cv-log",
        default=os.path.join(TMP_DIR, "configure-vm.log"),
        help="""The path to the log file that is used to log the output of the configuring VM.""",
    )
    parser.add_argument(
        "--configure-vm-template-path",
        default=os.path.join(RES_DIR, "configure-vm-template.xml.j2"),
        help="""The path to the template file that is used to configure the VM.""",
    )
    parser.add_argument(
        "--configure-vm-template-values",
        "-tv",
        metavar="KEY=VALUE",
        nargs="+",
        default=[],
        help="""An additional set of key=value pair arguments that should be passed to the --configure-vm-template.
        If a value contains spaces, you should define it with quotes.
        """,
    )
    parser.add_argument(
        "--reset-operations",
        default="defaults,-ssh-userdir",
        help="""The operations to perform during the reset operation.""",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Flag to enable verbose output.",
    )
    parser.add_argument(
        "--verbose-reset",
        "-vr",
        action="store_true",
        default=False,
        help="Flag to enable verbose output during the reset.",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=__version__,
        help="Print the version of the program",
    )


def corc_cli(commands):
    parser = commands.add_parser(
        "configure-image",
        help="Build the images defined in an architecture file.",
    )
    add_build_image_cli_arguments(parser)


def main(args):
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_build_image_cli_arguments(parser)
    args = parser.parse_args(args)

    image_path = os.path.realpath(os.path.expanduser(args.image_path))
    image_format = args.image_format
    configure_vm_template_path = os.path.realpath(
        os.path.expanduser(args.configure_vm_template_path)
    )
    user_data_path = os.path.realpath(os.path.expanduser(args.config_user_data_path))
    meta_data_path = os.path.realpath(os.path.expanduser(args.config_meta_data_path))
    vendor_data_path = os.path.realpath(
        os.path.expanduser(args.config_vendor_data_path)
    )
    network_config_path = os.path.realpath(
        os.path.expanduser(args.config_network_config_path)
    )
    configure_vm_name = args.configure_vm_name
    configure_vm_vcpus = args.configure_vm_vcpus
    configure_vm_cpu_model = args.configure_vm_cpu_model
    configure_vm_memory = args.configure_vm_memory
    cloud_init_iso_output_path = os.path.realpath(
        os.path.expanduser(args.cloud_init_iso_output_path)
    )
    log_file_path = os.path.realpath(os.path.expanduser(args.configure_vm_log_path))
    configure_vm_template_values = args.configure_vm_template_values
    reset_operations = args.reset_operations
    verbose = args.verbose
    verbose_reset = args.verbose_reset
    return_code, result_dict = configure_vm_image(
        image_path,
        image_format,
        configure_vm_template_path,
        user_data_path,
        meta_data_path,
        vendor_data_path,
        network_config_path,
        configure_vm_name,
        configure_vm_vcpus,
        configure_vm_cpu_model,
        configure_vm_memory,
        cloud_init_iso_output_path,
        log_file_path,
        configure_vm_template_values,
        reset_operations,
        verbose,
        verbose_reset,
    )
    response = {}
    if return_code == SUCCESS:
        response["status"] = "success"
    else:
        response["status"] = "failed"
    if verbose:
        response["outputs"] = result_dict.get("verbose_outputs", [])
    response["msg"] = result_dict.get("msg", "")
    response["return_code"] = return_code

    try:
        output = json.dumps(response, indent=4, sort_keys=True, default=to_str)
    except Exception as err:
        error_print(JSON_DUMP_ERROR_MSG.format(err))
        return JSON_DUMP_ERROR
    if return_code == SUCCESS:
        print(output)
    else:
        error_print(output)
    return return_code


def cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
