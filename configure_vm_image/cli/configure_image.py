import asyncio
import argparse
import os
import inspect
import sys
import json
from configure_vm_image._version import __version__
from configure_vm_image.common.utils import to_str, error_print, expand_path
from configure_vm_image.utils.io import exists, makedirs
from configure_vm_image.common.defaults import (
    CLOUD_INIT_DIR,
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
from configure_vm_image.cli.helpers import (
    extract_arguments,
    strip_argument_group_prefix,
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


def import_from_module(module_path, module_name, func_name):
    module = __import__(module_path, fromlist=[module_name])
    return getattr(module, func_name)


def add_cli_operations(
    parser,
    operation,
    module_cli_input_group_prefix="configure_vm_image.cli.input_groups",
    module_operation_prefix="configure_vm_image.cli.operations",
):
    operation_input_groups_func = import_from_module(
        "{}.{}".format(module_cli_input_group_prefix, operation),
        "{}".format(operation),
        "{}_groups".format(operation),
    )

    provider_groups = []
    argument_groups = []
    input_groups = operation_input_groups_func(parser)
    if not input_groups:
        raise RuntimeError(
            "No input groups were returned by the input group function: {}".format(
                operation_input_groups_func.func_name
            )
        )

    argument_groups = input_groups
    parser.set_defaults(
        func=cli_exec,
        module_path="{}.{}.build".format(module_operation_prefix, operation),
        module_name="build",
        func_name="{}_operation".format(operation),
        provider_groups=provider_groups,
        argument_groups=argument_groups,
    )


async def configure_vm_image(
    image_path,
    image_format=None,
    user_data_path=os.path.join(CLOUD_INIT_DIR, "user-data"),
    meta_data_path=os.path.join(CLOUD_INIT_DIR, "meta-data"),
    vendor_data_path=os.path.join(CLOUD_INIT_DIR, "vendor-data"),
    network_config_path=os.path.join(CLOUD_INIT_DIR, "network-config"),
    cloud_init_iso_output_path=os.path.join(CLOUD_INIT_DIR, "cidata.iso"),
    configure_vm_orchestrator="libvirt-provider",
    configure_vm_name="configure-vm-image",
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
        created = makedirs(os.path.dirname(configure_vm_log_path))
        if not created:
            response["msg"] = PATH_CREATE_ERROR_MSG.format(
                os.path.dirname(configure_vm_log_path)
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
    if "image_format" not in configure_vm_template_values:
        configure_vm_template_values.append(f"image_format={image_format}")

    configured_id, configured_msg = await configure_image(
        configure_vm_name,
        image_path,
        *configure_vm_template_values,
        template_path=configure_vm_template_path,
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
    return SUCCESS, "Succesfully configured image: {}".format(image_path)


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
        "--configure-vm-orchestrator",
        "-cv-orch",
        default="libvirt-provider",
        help="The orchestrator to use when provisioning the virtual machine that is used to configure a particular virtual machine image",
    )
    parser.add_argument(
        "--configure-vm-name",
        "-cv-name",
        default="configure-vm-image",
        help="The name of the VM that is used to configure the image.",
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


def cli_exec(arguments):
    # Actions determines which function to execute
    module_path = arguments.pop("module_path")
    module_name = arguments.pop("module_name")
    func_name = arguments.pop("func_name")

    if "positional_arguments" in arguments:
        positional_arguments = arguments.pop("positional_arguments")
    else:
        positional_arguments = []

    if "argument_groups" in arguments:
        argument_groups = arguments.pop("argument_groups")
    else:
        argument_groups = []

    func = import_from_module(module_path, module_name, func_name)
    if not func:
        return False, {}

    action_kwargs, _ = extract_arguments(arguments, argument_groups)
    action_kwargs = strip_argument_group_prefix(action_kwargs, argument_groups)

    action_args = positional_arguments
    if inspect.iscoroutinefunction(func):
        return asyncio.run(func(*action_args, **action_kwargs))
    return func(*action_args, **action_kwargs)


def add_base_cli_operations(parser):
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
    # Add the basic CLI functions
    add_base_cli_operations(parser)
    # Add the configure image CLI arguments
    add_configure_vm_image_cli_arguments(parser)
    parsed_args = parser.parse_args(args)
    # Convert to a dictionary
    arguments = vars(parsed_args)

    if "func" not in arguments:
        raise ValueError("Missing function to execute in prepared arguments")

    func = arguments.pop("func")
    return_code, result_dict = func(arguments)

    return_code, result_dict = configure_vm_image(
        expand_path(args.image_path),
        image_format=args.image_format,
        user_data_path=expand_path(args.config_user_data_path),
        meta_data_path=expand_path(args.config_meta_data_path),
        vendor_data_path=expand_path(args.config_vendor_data_path),
        network_config_path=expand_path(args.config_network_config_path),
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
