import os
import time
from configure_vm_image.common.codes import (
    PATH_CREATE_ERROR,
    PATH_CREATE_ERROR_MSG,
    PATH_NOT_FOUND_ERROR,
    PATH_NOT_FOUND_ERROR_MSG,
    CONFIGURE_IMAGE_ERROR,
    CONFIGURE_IMAGE_ERROR_MSG,
)
from configure_vm_image.utils.job import run
from configure_vm_image.utils.io import exists, which, load


def discover_create_iso_command():
    """Discovers the command to generate an iso on the system"""
    if os.uname().sysname == "Darwin":
        create_iso_command = "mkisofs"
    else:
        create_iso_command = "genisoimage"
    if not which(create_iso_command):
        raise FileNotFoundError(
            "Failed to find the {} command on the system. Please ensure that it is installed".format(
                create_iso_command
            )
        )
    return create_iso_command


def create_cloud_init_disk(
    output_path,
    user_data_path=None,
    meta_data_path=None,
    vendor_data_path=None,
    network_config_path=None,
):
    # Generated the configuration iso image
    # Notice that we label the iso cidata to ensure that cloud-init
    # recognizes the disk as a configuration disk
    create_iso_command = discover_create_iso_command()
    cloud_init_command = [
        create_iso_command,
        "-output",
        output_path,
        "-V",
        "cidata",
        "--joliet",
        "--rock",
    ]

    if user_data_path:
        cloud_init_command.append(user_data_path)
    if meta_data_path:
        cloud_init_command.append(meta_data_path)
    if vendor_data_path:
        cloud_init_command.append(vendor_data_path)
    if network_config_path:
        cloud_init_command.append(network_config_path)
    success, result = run(cloud_init_command)
    if not success:
        return PATH_CREATE_ERROR, PATH_CREATE_ERROR_MSG.format(
            output_path, result["error"]
        )
    return True, result["output"]


def virt_customize(image_path, commands_from_file):
    if not exists(image_path):
        return PATH_NOT_FOUND_ERROR, PATH_NOT_FOUND_ERROR_MSG.format(
            image_path, "could not find the image path to customize"
        )

    if not exists(commands_from_file):
        return PATH_NOT_FOUND_ERROR, PATH_NOT_FOUND_ERROR_MSG.format(
            commands_from_file,
            "could not find the commands file to customize the image with",
        )

    # Run the virt-customize command
    virt_customize_command = [
        "virt-customize",
        "-a",
        image_path,
        "--commands-from-file",
        commands_from_file,
    ]
    result = run(virt_customize_command)
    if result["returncode"] != "0":
        return CONFIGURE_IMAGE_ERROR, CONFIGURE_IMAGE_ERROR_MSG.format(
            image_path, result["error"]
        )

    return result, None


def generate_image_configuration(
    output_path,
    user_data_path=None,
    meta_data_path=None,
    vendor_data_path=None,
    network_config_path=None,
):
    return create_cloud_init_disk(
        output_path,
        user_data_path=user_data_path,
        meta_data_path=meta_data_path,
        vendor_data_path=vendor_data_path,
        network_config_path=network_config_path,
    )


def discover_vm_orchestrator():
    """Discovers the kvm command on the system"""
    orchestrator = "libvirt-provider"
    if not which(orchestrator):
        raise FileNotFoundError(
            "Failed to find the {} command on the system. Please ensure that it is installed".format(
                orchestrator
            )
        )
    return orchestrator


def configure_vm(name, image, *template_args, **kwargs):
    """This launches a subprocess that configures the VM image on boot."""
    vm_orchestrator = discover_vm_orchestrator()
    create_command = [
        vm_orchestrator,
        "instance",
        "create",
        name,
        image,
        "--extra-template-path-values",
        *template_args,
    ]
    for key, value in kwargs.items():
        if value:
            configure_key = "--{}".format(key).replace("_", "-")
            create_command.extend([configure_key, value])
    create_success, create_result = run(create_command, output_format="json")
    if not create_success:
        return False, create_result["error"]

    if not isinstance(create_result, dict):
        return False, create_result

    if "error" in create_result and create_result["error"]:
        return False, create_result["error"]

    if "output" in create_result and not create_result["output"]:
        return False, create_result["output"]

    if not isinstance(create_result["output"], dict):
        return False, create_result["output"]

    if "instance" not in create_result["output"]:
        return False, create_result["output"]

    if not isinstance(create_result["output"]["instance"], dict):
        return False, create_result["output"]

    if "id" not in create_result["output"]["instance"]:
        return False, create_result["output"]["instance"]

    instance_id = create_result["output"]["instance"]["id"]
    start_command = [
        vm_orchestrator,
        "instance",
        "start",
        instance_id,
    ]
    start_success, start_result = run(start_command, output_format="json")
    if not start_success:
        return False, start_result["error"]
    return instance_id, start_result["output"]


def configure_image(name, image, *template_args, **configure_kwargs):
    """Configures the image using the configuration path"""
    configure_result, configure_msg = configure_vm(
        name, image, *template_args, **configure_kwargs
    )
    if not configure_result:
        return False, configure_msg
    return configure_result, configure_msg


def finished_configure(configure_vm_log_path):
    """Waits for the configuration process to finish"""
    # Wait for the configuration process to finish
    if not exists(configure_vm_log_path):
        return False

    first_marker = "Cloud-init v"
    second_marker = "finished at"

    finished = False
    while not finished:
        loaded, content = load(configure_vm_log_path, readlines=True)
        if loaded:
            for line in content:
                if first_marker in line and second_marker in line:
                    finished = True
    return finished


def vm_action(action, name, *args, **kwargs):
    vm_orchestrator = discover_vm_orchestrator()
    command = [vm_orchestrator, "instance", action, name, *args]
    for key, value in kwargs.items():
        if key and value:
            command.extend([key, value])
        elif key and not value:
            command.append(key)
        elif value and not key:
            command.append(value)
    success, result = run(command, output_format="json")
    if not success:
        return False, result["error"]
    return True, result["output"]


def wait_for_vm_shutdown(name, attempts=30):
    """Waits for the VM to be shutdown"""
    attempt = 0
    while attempt < attempts:
        found, result = vm_action("show", name)
        if found:
            instance = result.get("instance", {})
            state = instance.get("state", "")
            if state == "shut off":
                return True, f"VM: {name} was successfully shutdown"
        else:
            return True, f"VM: {name} was is already removed"
        time.sleep(1)
        attempt += 1
    return False, f"Failed to wait for the shutdown of VM: {name}"


def wait_for_vm_removed(name, attempts=30):
    """Waits for the VM to be removed"""
    attempt = 0
    msg = ""
    while attempt < attempts:
        found, msg = vm_action("show", name)
        if not found:
            return True, f"VM: {name} was sucessfully removed"
        time.sleep(1)
        attempt += 1
    if not msg:
        msg = f"Failed to wait for the removal of VM: {name}"
    return False, msg


def reset_image(image, reset_operations=None, verbose=False):
    """Resets the image such that it is ready to be started
    in production"""
    # Ensure that the virt-sysprep doesn't try to use libvirt
    # but qemu instead
    # LIBGUESTFS_BACKEND=direct
    reset_command = ["virt-sysprep", "-a", image]
    if reset_operations:
        reset_command.extend(["--operations", reset_operations])
    if verbose:
        reset_command.append("--verbose")
    success, result = run(reset_command)
    if not success:
        return False, result["error"]
    return True, result["output"]
