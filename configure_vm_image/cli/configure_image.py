import argparse
import os
import sys
import json
from configure_vm_image._version import __version__
from configure_vm_image.common.utils import to_str, error_print, expand_path
from configure_vm_image.utils.io import exists, makedirs
from configure_vm_image.common.defaults import (
    CLOUD_INIT_DIR,
    PACKAGE_NAME,
    TMP_DIR,
    RES_DIR,
)
from configure_vm_image.common.codes import (
    SUCCESS,
    CONFIGURE_IMAGE_ERROR,
    CONFIGURE_IMAGE_ERROR_MSG,
    PATH_CREATE_ERROR,
    PATH_CREATE_ERROR_MSG,
    PATH_NOT_FOUND_ERROR,
    PATH_NOT_FOUND_ERROR_MSG,
    JSON_DUMP_ERROR,
    JSON_DUMP_ERROR_MSG,
    RESET_IMAGE_ERROR,
    RESET_IMAGE_ERROR_MSG,
)
from configure_vm_image.configure import (
    reset_image,
    wait_for_vm_removed,
    wait_for_vm_shutdown,
    vm_action,
    configure_image,
    finished_configure,
    generate_image_configuration,
)

SCRIPT_NAME = __file__


def configure_vm_image(
    image_path,
    image_format=None,
    user_data_path=os.path.join(CLOUD_INIT_DIR, "user-data"),
    meta_data_path=os.path.join(CLOUD_INIT_DIR, "meta-data"),
    vendor_data_path=os.path.join(CLOUD_INIT_DIR, "vendor-data"),
    network_config_path=os.path.join(CLOUD_INIT_DIR, "network-config"),
    configure_vm_name=PACKAGE_NAME,
    configure_vm_cpu_model=None,
    configure_vm_vcpus="1",
    configure_vm_memory="2048MiB",
    cloud_init_iso_output_path=os.path.join(CLOUD_INIT_DIR, "cidata.iso"),
    configure_vm_log_path=os.path.join(TMP_DIR, "configure-vm.log"),
    configure_vm_template_path=os.path.join(RES_DIR, "configure-vm-template.xml.j2"),
    configure_vm_template_values=None,
    reset_operations="defaults,-ssh-userdir",
    verbose=False,
    verbose_reset=False,
):
    response = {}
    verbose_outputs = []

    if not configure_vm_template_values:
        configure_vm_template_values = []

    # Ensure that the image to configure exists
    if not exists(image_path):
        response["msg"] = PATH_NOT_FOUND_ERROR_MSG.format(
            image_path, "could not find the image to configure"
        )
        response["verbose_outputs"] = verbose_outputs
        return PATH_NOT_FOUND_ERROR, response

    if not image_format:
        image_format = os.path.splitext(image_path)[1].replace(".", "")
        if verbose:
            verbose_outputs.append(
                "Automatically discovered image format: {} to configure the disk image".format(
                    image_format
                )
            )

    # Ensure that the required output directories exists
    cidata_iso_dir = os.path.dirname(cloud_init_iso_output_path)
    for d in [cidata_iso_dir]:
        if not exists(d):
            created = makedirs(d)
            if not created:
                response["msg"] = PATH_CREATE_ERROR_MSG.format(d)
                response["verbose_outputs"] = verbose_outputs
                return PATH_CREATE_ERROR, response

    if not exists(user_data_path):
        verbose_outputs.append(
            PATH_NOT_FOUND_ERROR_MSG.format(
                user_data_path,
                "could not find the user-data configuration file, continuing without it",
            )
        )
        user_data_path = None

    if not exists(meta_data_path):
        verbose_outputs.append(
            PATH_NOT_FOUND_ERROR_MSG.format(
                meta_data_path,
                "could not find the meta-data configuration file, continuing without it",
            )
        )
        meta_data_path = None

    if not exists(vendor_data_path):
        verbose_outputs.append(
            PATH_NOT_FOUND_ERROR_MSG.format(
                vendor_data_path,
                "could not find the vendor-data configuration file, continuing without it",
            )
        )
        vendor_data_path = None

    if not exists(network_config_path):
        verbose_outputs.append(
            PATH_NOT_FOUND_ERROR_MSG.format(
                network_config_path,
                "could not find the network-config configuration file, continuing without it",
            )
        )
        network_config_path = None
    if verbose:
        verbose_outputs.append(
            "Generating the cloud-init iso image at: {}".format(
                cloud_init_iso_output_path
            )
        )

    generated_result, generated_msg = generate_image_configuration(
        cloud_init_iso_output_path,
        user_data_path=user_data_path,
        meta_data_path=meta_data_path,
        vendor_data_path=vendor_data_path,
        network_config_path=network_config_path,
    )
    if verbose:
        verbose_outputs.append(generated_msg)
    if not generated_result:
        response["msg"] = generated_msg
        response["verbose_outputs"] = verbose_outputs
        return generated_result, response

    if not exists(os.path.dirname(configure_vm_log_path)):
        created, msg = makedirs(os.path.dirname(configure_vm_log_path))
        if not created:
            response["msg"] = PATH_CREATE_ERROR_MSG.format(
                os.path.dirname(configure_vm_log_path), msg
            )
            response["verbose_outputs"] = verbose_outputs
            return PATH_CREATE_ERROR, response

    incrementer = 0
    while exists(configure_vm_log_path):
        if incrementer == 0:
            if verbose:
                verbose_outputs.append(
                    f"The configuring log file: {configure_vm_log_path} already exists, increasing the designated file name"
                )
            configure_vm_log_path = f"{configure_vm_log_path}.%s" % incrementer
        else:
            file_increment = os.path.splitext(configure_vm_log_path)[1]
            configure_vm_log_path = configure_vm_log_path.replace(
                file_increment, f".{incrementer + 1}"
            )
        incrementer += 1
    if verbose:
        verbose_outputs.append(f"Generated new log file path: {configure_vm_log_path}")
        verbose_outputs.append(
            f"Using the VM template description: {configure_vm_template_path}"
        )

    # Ensure that the required template values are set for the cloud-init iso image
    # and for the VM log file that is monitored to tell when the configuration process is finished
    if "cd_iso_path" not in configure_vm_template_values:
        configure_vm_template_values.append(f"cd_iso_path={cloud_init_iso_output_path}")
    if "configure_vm_log_path" not in configure_vm_template_values:
        configure_vm_template_values.append(f"log_file_path={configure_vm_log_path}")

    configured_id, configured_msg = configure_image(
        configure_vm_name,
        image_path,
        *configure_vm_template_values,
        template_path=configure_vm_template_path,
        disk_driver_type=image_format,
        cpu_mode=configure_vm_cpu_model,
        num_vcpus=configure_vm_vcpus,
        memory_size=configure_vm_memory,
    )
    if verbose:
        verbose_outputs.append(configured_msg)
    if not configured_id:
        response["msg"] = CONFIGURE_IMAGE_ERROR_MSG.format(
            image_path, "failed to configure image"
        )
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response

    if verbose:
        verbose_outputs.append("Waiting for the configuration process to finish")
    finished = finished_configure(configure_vm_log_path)
    if not finished:
        response["msg"] = "Failed to finish configuring the image"
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response
    if verbose:
        verbose_outputs.append(
            f"Finished configuring the image in the instance: {configured_id}"
        )

    shutdown, shutdown_msg = vm_action("stop", configured_id)
    if not shutdown:
        response["msg"] = (
            f"Failed to shutdown the VM: {configured_id} after configuration: {shutdown_msg}"
        )
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response

    shutdowned, shutdowned_msg = wait_for_vm_shutdown(configured_id)
    if not shutdowned:
        response["msg"] = (
            f"Failed to wait for the shutdown of VM: {configured_id} after configuration: {shutdowned_msg}"
        )
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response

    remove, remove_msg = vm_action("remove", configured_id)
    if not remove:
        response["msg"] = (
            f"Failed to remove the VM: {configured_id} after configuration: {remove_msg}"
        )
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response

    removed, removed_msg = wait_for_vm_removed(configured_id)
    if not removed:
        response["msg"] = (
            f"Failed to wait for the removal of VM: {configured_id} after the configuration was applied: {removed_msg}"
        )
        response["verbose_outputs"] = verbose_outputs
        return CONFIGURE_IMAGE_ERROR, response
    if verbose:
        verbose_outputs.append(
            f"Removed the VM: {configured_id} after configuration: {removed_msg}"
        )

    reset_success, reset_results = reset_image(
        image_path, reset_operations=reset_operations, verbose=verbose_reset
    )
    if verbose:
        verbose_outputs.append(reset_results)
    if not reset_success:
        response["msg"] = RESET_IMAGE_ERROR_MSG.format(
            reset_results, "failed to reset image"
        )
        response["verbose_outputs"] = verbose_outputs
        return RESET_IMAGE_ERROR, response


def add_configure_vm_image_cli_arguments(parser):
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


def main(args):
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_configure_vm_image_cli_arguments(parser)
    args = parser.parse_args(args)

    return_code, result_dict = configure_vm_image(
        expand_path(args.image_path),
        image_format=args.image_format,
        user_data_path=expand_path(args.config_user_data_path),
        meta_data_path=expand_path(args.config_meta_data_path),
        vendor_data_path=expand_path(args.config_vendor_data_path),
        network_config_path=expand_path(args.config_network_config_path),
        configure_vm_name=args.configure_vm_name,
        configure_vm_cpu_model=args.configure_vm_cpu_model,
        configure_vm_vcpus=args.configure_vm_vcpus,
        configure_vm_memory=args.configure_vm_memory,
        cloud_init_iso_output_path=expand_path(args.cloud_init_iso_output_path),
        configure_vm_log_path=expand_path(args.configure_vm_log_path),
        configure_vm_template_path=expand_path(args.configure_vm_template_path),
        configure_vm_template_values=args.configure_vm_template_values,
        reset_operations=args.reset_operations,
        verbose=args.verbose,
        verbose_reset=args.verbose_reset,
    )
    response = {}
    if return_code == SUCCESS:
        response["status"] = "success"
    else:
        response["status"] = "failed"
    if args.verbose:
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
