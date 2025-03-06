import os
import time
from configure_vm_image.common.defaults import (
    CLOUD_INIT_DIR,
    TMP_DIR,
    RES_DIR,
    CONFIGURE_VM_VCPUS,
    CONFIGURE_VM_MEMORY,
    CONFIGURE_VM_MACHINE,
    CPU_ARCHITECTURE,
)
from configure_vm_image.common.codes import (
    SUCCESS,
    CONFIGURE_IMAGE_ERROR,
    CONFIGURE_IMAGE_ERROR_MSG,
    PATH_CREATE_ERROR,
    PATH_CREATE_ERROR_MSG,
    PATH_NOT_FOUND_ERROR,
    PATH_NOT_FOUND_ERROR_MSG,
    RESET_IMAGE_ERROR,
    RESET_IMAGE_ERROR_MSG,
)
from configure_vm_image.utils.job import run
from configure_vm_image.utils.io import exists, which, load, makedirs


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
    """Discovers the vm orchestrator command line tool on the system"""
    # TODO, accept the orchestrator as an argument to be dynamically discovered
    orchestrator = "libvirt-provider"
    if not which(orchestrator):
        raise FileNotFoundError(
            "Failed to find the {} command on the system. Please ensure that it is installed".format(
                orchestrator
            )
        )
    return orchestrator


async def configure_vm(name, image, template_path=None, **kwargs):
    """This launches a subprocess that configures the VM image on boot."""
    vm_orchestrator = discover_vm_orchestrator()
    # TODO discover the specific vm orchestrator argument structure
    create_command = [
        vm_orchestrator,
        "instance",
        "create",
        name,
        image,
    ]
    if template_path:
        create_command.extend(["--template-path", template_path])
        create_command.extend(["--extra-template-path-values"])
        create_command.append(
            ",".join([f"{key}={value}" for key, value in kwargs.items()])
        )

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


async def configure_image(name, image, **kwargs):
    """Configures the image using the configuration path"""
    configure_result, configure_msg = await configure_vm(name, image, **kwargs)
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
        content = load(configure_vm_log_path, readlines=True)
        if content and isinstance(content, (list, set, tuple)):
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
):
    response = {}
    verbose_outputs = []

    if not configure_vm_template_values:
        configure_vm_template_values = {}

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

    # TODO, these does not validate the template values correctly
    # Ensure that the required template values are set for the cloud-init iso image
    # and for the VM log file that is monitored to tell when the configuration process is finished
    if "num_vcpus" not in configure_vm_template_values:
        configure_vm_template_values["num_vcpus"] = CONFIGURE_VM_VCPUS
    if "memory_size" not in configure_vm_template_values:
        configure_vm_template_values["memory_size"] = CONFIGURE_VM_MEMORY
    if "cpu_architecture" not in configure_vm_template_values:
        configure_vm_template_values["cpu_architecture"] = CPU_ARCHITECTURE
    if "machine" not in configure_vm_template_values:
        configure_vm_template_values["machine"] = CONFIGURE_VM_MACHINE
    if "cd_iso_path" not in configure_vm_template_values:
        configure_vm_template_values["cd_iso_path"] = cloud_init_iso_output_path
    if (
        "configure_vm_log_path" not in configure_vm_template_values
        and "log_file_path" not in configure_vm_template_values
    ):
        configure_vm_template_values["log_file_path"] = configure_vm_log_path

    configured_id, configured_msg = await configure_image(
        configure_vm_name,
        image_path,
        template_path=configure_vm_template_path,
        **configure_vm_template_values,
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
        image_path, reset_operations=reset_operations, verbose=verbose
    )
    if verbose:
        verbose_outputs.append(reset_results)
    if not reset_success:
        response["msg"] = RESET_IMAGE_ERROR_MSG.format(
            reset_results, "failed to reset image"
        )
        response["verbose_outputs"] = verbose_outputs
        return RESET_IMAGE_ERROR, response
    response["msg"] = "Succesfully configured image: {}".format(image_path)
    return SUCCESS, response
