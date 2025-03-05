import os
from configure_vm_image.common.defaults import (
    CLOUD_INIT_DIR,
    TMP_DIR,
    RES_DIR,
)
from configure_vm_image.cli.parsers.configure import configure_group
from configure_vm_image.configure import configure_vm_image
from configure_vm_image.common.utils import expand_path


def configure_vm_image_cli(commands):
    parser = commands.add_parser(
        "configure-vm",
    )
    configure_group(parser)
    parser.set_defaults(func=corc_configure_vm_cli_exec)


def corc_configure_vm_cli_exec(args):
    image_path = args.get("image_path")
    image_format = args.get("image_format", None)
    config_user_data_path = args.get(
        "config_user_data_path", os.path.join(CLOUD_INIT_DIR, "user-data")
    )
    config_meta_data_path = args.get(
        "config_meta_data_path", os.path.join(CLOUD_INIT_DIR, "meta-data")
    )
    config_vendor_data_path = args.get(
        "config_vendor_data_path", os.path.join(CLOUD_INIT_DIR, "vendor-data")
    )
    config_network_config_path = args.get(
        "config_network_config_path", os.path.join(CLOUD_INIT_DIR, "network-config")
    )
    cloud_init_iso_output_path = args.get(
        "cloud_init_iso_output_path", os.path.join(CLOUD_INIT_DIR, "cidata.iso")
    )
    configure_vm_name = args.get("configure_vm_name", "configure-vm-image")
    configure_vm_log_path = args.get(
        "configure_vm_log_path", os.path.join(TMP_DIR, "configure-vm.log")
    )
    configure_vm_template_path = args.get(
        "configure_vm_template_path",
        os.path.join(RES_DIR, "configure-vm-template.xml.j2"),
    )
    configure_vm_template_values = args.get("configure_vm_template_values", {})
    reset_operations = args.get("reset_operations", "defaults,-ssh-userdir")
    verbose = args.get("verbose", False)

    return configure_vm_image(
        expand_path(image_path),
        image_format=image_format,
        user_data_path=expand_path(config_user_data_path),
        meta_data_path=expand_path(config_meta_data_path),
        vendor_data_path=expand_path(config_vendor_data_path),
        network_config_path=expand_path(config_network_config_path),
        cloud_init_iso_output_path=expand_path(cloud_init_iso_output_path),
        configure_vm_name=configure_vm_name,
        configure_vm_log_path=expand_path(configure_vm_log_path),
        configure_vm_template_path=expand_path(configure_vm_template_path),
        configure_vm_template_values=configure_vm_template_values,
        reset_operations=reset_operations,
        verbose=verbose,
    )
