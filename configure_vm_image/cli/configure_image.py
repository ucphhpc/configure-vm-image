import argparse
import os
import socket
from configure_vm_image.common.defaults import CLOUD_INIT_DIR, PACKAGE_NAME
from configure_vm_image.common.errors import (
    PATH_CREATE_ERROR,
    PATH_CREATE_ERROR_MSG,
    PATH_NOT_FOUND_ERROR,
    PATH_NOT_FOUND_ERROR_MSG,
    CONFIGURE_IMAGE_ERROR,
    CONFIGURE_IMAGE_ERROR_MSG,
    RESET_IMAGE_ERROR,
    RESET_IMAGE_ERROR_MSG,
)
from configure_vm_image.utils.job import run
from configure_vm_image.utils.io import exists, makedirs, which

SCRIPT_NAME = __file__


def discover_create_iso_command():
    """Discovers the kvm command on the system"""
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
    verbose=False,
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


def discover_kvm_command():
    """Discovers the kvm command on the system"""
    kvm_command = "kvm"
    if not which(kvm_command):
        kvm_command = "qemu-kvm"
    if not which(kvm_command):
        kvm_command = "qemu-system-x86_64"
    if not which(kvm_command):
        raise FileNotFoundError(
            "Failed to find the kvm command on the system. Please ensure that it is installed"
        )
    return kvm_command


def discover_configure_vm_command():
    """Discovers the kvm command on the system"""
    configure_vm_command = "libvirt-provider"
    if not which(configure_vm_command):
        raise FileNotFoundError(
            "Failed to find the {} command on the system. Please ensure that it is installed".format(
                configure_vm_command
            )
        )
    return configure_vm_command


def read_socket_until_empty(socket, buffer_size=1024):
    msg = ""
    response = socket.recv(buffer_size).decode("utf-8")
    while response != "":
        msg += response
        response = socket.recv(buffer_size).decode("utf-8")
    return msg


def configure_vm(name, image, configuration_path, **kwargs):
    """This launches a subprocess that configures the VM image on boot."""
    configure_vm_command = discover_configure_vm_command()
    create_command = [configure_vm_command, "instance", "create", name, image]
    for key, value in kwargs.items():
        if value:
            configure_key = "--{}".format(key).replace("_", "-")
            create_command.extend([configure_key, value])
    create_success, create_result = run(create_command, output_format="json")
    if not create_success:
        return False, create_result["error"]

    if "id" not in create_result["output"]["instance"]:
        return False, create_result["output"]

    start_command = [
        configure_vm_command,
        "instance",
        "start",
        create_result["output"]["instance"]["id"],
    ]
    start_success, start_result = run(start_command, output_format="json")
    if not start_success:
        return False, start_result["error"]
    return True, start_result["output"]


def shutdown_vm(input_queue, qemu_socket_path):
    stopped = False
    while not stopped:
        value = input_queue.get()
        print("Read configuring output: {}".format(value))
        if "Activate the web console with:" in value:
            print("Found finished configuration message: {}".format(value))
            # Connect to the qemu monitor socket and send the shutdown command
            _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                _socket.connect(qemu_socket_path)
                _socket.sendall("system_powerdown\n".encode("utf-8"))
                print("Sent shutdown message")
                msg = read_socket_until_empty(_socket)
                print("Received shutdown message: {}".format(msg))
            except Exception as err:
                print("Failed to connect to qemu monitor socket: {}".format(err))
            finally:
                _socket.close()
        if "Power down" in value:
            stopped = True
    print("Finished the shutdown VM process")


def configure_image(name, image, configuration_path, **configure_kwargs):
    """Configures the image using the configuration path"""
    configure_result, configure_msg = configure_vm(
        name, image, configuration_path, **configure_kwargs
    )
    if not configure_result:
        print("Failed to configure the image: {}".format(name))
        return False, configure_msg
    return True, configure_msg

def finished_configure(log_file_path):
    """Waits for the configuration process to finish"""
    # Wait for the configuration process to finish
    finished = False
    while not finished:
        if not exists(log_file_path):
            continue
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            if "Finished configuring the image" in log_content:
                finished = True
    return finished


def reset_image(image, reset_operations=None):
    """Resets the image such that it is ready to be started
    in production"""
    # Ensure that the virt-sysprep doesn't try to use libvirt
    # but qemu instead
    # LIBGUESTFS_BACKEND=direct
    reset_command = ["virt-sysprep", "-a", image]
    if reset_operations:
        reset_command.extend(["--operations", reset_operations])
    success, result = run(reset_command)
    if not success:
        return False, result["error"]
    return True, result["output"]


def run_configure_image():
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "image_path",
        help="The path to the image that is to be configured.",
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
        "--cloud-init-iso-output-path",
        "-ci-output",
        default=os.path.join(CLOUD_INIT_DIR, "cidata.iso"),
        help="""The path to the cloud-init output iso image file that is generated
        based on the data defined in the user-data, meta-data, vendor-data, and network-config files.
        This seed iso file is then subsequently used to configure the defined input image.""",
    )
    parser.add_argument(
        "--configure-vm-name",
        "-n",
        default=PACKAGE_NAME,
        help="""The name of the VM that is used to configure the image.""",
    )
    parser.add_argument(
        "--configure-vm-template",
        "-t",
        default=None,
        help="""The path to the template file that specifies how the configuring VM should be launched.""",
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
        default=1,
        help="""The number of virtual CPUs to allocate to the VM when configuring the image.""",
    )
    parser.add_argument(
        "--configure-vm-memory",
        "-cv-m",
        default="2048MiB",
        help="""The amount of memory to allocate to the VM when configuring the image.""",
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
        help="Flag to enable verbose output",
    )
    args = parser.parse_args()

    image_path = args.image_path
    user_data_path = args.config_user_data_path
    meta_data_path = args.config_meta_data_path
    vendor_data_path = args.config_vendor_data_path
    network_config_path = args.config_network_config_path
    cloud_init_iso_output_path = args.cloud_init_iso_output_path
    configure_vm_name = args.configure_vm_name
    configure_vm_template = args.configure_vm_template
    configure_vm_vcpus = args.configure_vm_vcpus
    configure_vm_cpu_model = args.configure_vm_cpu_model
    configure_vm_memory = args.configure_vm_memory
    reset_operations = args.reset_operations
    verbose = args.verbose

    # Ensure that the image to configure exists
    if not exists(image_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                image_path, "could not find the image to configure"
            )
        )
        exit(PATH_NOT_FOUND_ERROR)

    # Ensure that the required output directories exists
    cidata_iso_dir = os.path.dirname(cloud_init_iso_output_path)
    for d in [cidata_iso_dir]:
        if not exists(d):
            created, msg = makedirs(d)
            if not created:
                print(PATH_CREATE_ERROR_MSG.format(d, msg))
                exit(PATH_CREATE_ERROR)

    if not exists(user_data_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                user_data_path,
                "could not find the user-data configuration file, continuing without it",
            )
        )
        user_data_path = None

    if not exists(meta_data_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                meta_data_path,
                "could not find the meta-data configuration file, continuing without it",
            )
        )
        meta_data_path = None

    if not exists(vendor_data_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                vendor_data_path,
                "could not find the vendor-data configuration file, continuing without it",
            )
        )
        vendor_data_path = None

    if not exists(network_config_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                network_config_path,
                "could not find the network-config configuration file, continuing without it",
            )
        )
        network_config_path = None

    generated_result, generated_msg = generate_image_configuration(
        cloud_init_iso_output_path,
        user_data_path=user_data_path,
        meta_data_path=meta_data_path,
        vendor_data_path=vendor_data_path,
        network_config_path=network_config_path,
    )
    if not generated_result:
        print(generated_msg)
        exit(generated_result)
    if verbose:
        print(generated_msg)

    configured, configured_msg = configure_image(
        configure_vm_name,
        image_path,
        cloud_init_iso_output_path,
        template_path=configure_vm_template,
        cpu_mode=configure_vm_cpu_model,
        memory_size=configure_vm_memory,
    )
    if verbose:
        print(configured_msg)
    if not configured:
        print(CONFIGURE_IMAGE_ERROR_MSG.format(image_path, "failed to configure image"))
        exit(CONFIGURE_IMAGE_ERROR)

    finished = finished_configure(log_file_path)
    if not finished:
        print("Failed to finish configuring the image")
        exit(CONFIGURE_IMAGE_ERROR)

    reset_success, reset_results = reset_image(
        image_path, reset_operations=reset_operations
    )
    if verbose:
        print(reset_results)
    if not reset_success:
        print(RESET_IMAGE_ERROR_MSG.format(reset_results, "failed to reset image"))
        exit(RESET_IMAGE_ERROR)


if __name__ == "__main__":
    run_configure_image()
