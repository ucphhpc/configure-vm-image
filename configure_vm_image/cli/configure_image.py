import argparse
import os
import subprocess
import socket
import multiprocessing as mp
from configure_vm_image.common.defaults import (
    CLOUD_CONFIG_DIR,
    IMAGE_CONFIG_DIR,
    CONFIGURE_IMAGE_DIR,
)
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
from configure_vm_image.utils.job import run, run_popen
from configure_vm_image.utils.io import exists, makedirs, which

SCRIPT_NAME = __file__


def create_cloud_init_disk(
    user_data_path, meta_data_path, vendor_data_path, output_path
):
    # Generated the configuration image
    cloud_init_command = [
        "cloud-localds",
        output_path,
        user_data_path,
        meta_data_path,
        "-V",
        vendor_data_path,
    ]
    localds_result = run(cloud_init_command, format_output_str=True)
    if localds_result["returncode"] != "0":
        return PATH_CREATE_ERROR, PATH_CREATE_ERROR_MSG.format(
            output_path, localds_result["error"]
        )

    return localds_result, None


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
    result = subprocess.run(virt_customize_command, format_output_str=True)
    if result["returncode"] != "0":
        return CONFIGURE_IMAGE_ERROR, CONFIGURE_IMAGE_ERROR_MSG.format(
            image_path, result["error"]
        )

    return result, None


def generate_image_configuration(
    user_data_path, meta_data_path, vendor_data_path, output_path
):
    # Setup the cloud init configuration
    # Generate a disk with user-supplied data
    if not exists(user_data_path):
        return PATH_NOT_FOUND_ERROR, PATH_NOT_FOUND_ERROR_MSG.format(user_data_path)

    if not exists(meta_data_path):
        return PATH_NOT_FOUND_ERROR, PATH_NOT_FOUND_ERROR_MSG.format(meta_data_path)

    if not exists(vendor_data_path):
        return PATH_NOT_FOUND_ERROR, PATH_NOT_FOUND_ERROR_MSG.format(vendor_data_path)

    return create_cloud_init_disk(
        user_data_path, meta_data_path, vendor_data_path, output_path
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


def read_socket_until_empty(socket, buffer_size=1024):
    msg = ""
    response = socket.recv(buffer_size).decode("utf-8")
    while response != "":
        msg += response
        response = socket.recv(buffer_size).decode("utf-8")
    return msg


def configure_vm(
    image,
    configuration_path,
    qemu_socket_path,
    cpu_model,
    output_queue,
    configure_vm_name="vm",
    memory="2048",
):
    """This launches a subprocess that configures the VM image on boot."""
    kvm_command = discover_kvm_command()
    configure_command = [
        kvm_command,
        "-name",
        configure_vm_name,
        "-cpu",
        cpu_model,
        "-m",
        memory,
        "-nographic",
        # https://unix.stackexchange.com/questions/426652/connect-to-running-qemu-instance-with-qemu-monitor
        # Allow the qemu instance to be shutdown via a socket signal
        "-monitor",
        "unix:{},server,nowait".format(qemu_socket_path),
        "-hda",
        image,
        "-hdb",
        configuration_path,
    ]

    configuring_results = run_popen(
        configure_command, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1
    )
    for line in iter(configuring_results["output"].readline, b""):
        if line == "":
            break
        output_queue.put(line)
    configuring_results["output"].close()
    try:
        communicate_output = configuring_results["communicate"](timeout=10)
    except subprocess.TimeoutExpired:
        configuring_results["kill"]()
        communicate_output = configuring_results["communicate"]()
    print("Finished the configure VM process: {}".format(communicate_output))
    return True


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


def configure_image(image, configuration_path, qemu_socket_path, cpu_model="host"):
    """Configures the image by booting the image with qemu to allow
    for cloud init to apply the configuration"""
    queue = mp.Queue()
    configuring_vm = mp.Process(
        target=configure_vm,
        args=(
            image,
            configuration_path,
            qemu_socket_path,
            cpu_model,
            queue,
        ),
    )
    shutdowing_vm = mp.Process(target=shutdown_vm, args=(queue, qemu_socket_path))

    # Start the sub processes
    configuring_vm.start()
    shutdowing_vm.start()

    # Wait for them to finish
    shutdowing_vm.join()
    # The configuring_vm is stopped by the shutdown_vm process
    # and therefore should operate as a detached process that should not be joined/waited for.
    configuring_vm.join()
    return True


def reset_image(image):
    """Resets the image such that it is ready to be started
    in production"""
    # Ensure that the virt-sysprep doesn't try to use libvirt
    # but qemu instead
    # LIBGUESTFS_BACKEND=direct
    reset_command = ["virt-sysprep", "-a", image]
    reset_result = run(reset_command)
    if reset_result["returncode"] != 0:
        print("Failed to reset image: {}".format(reset_result))
        return False
    return True


def run_configure_image():
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--image-input-path",
        default=os.path.join(CONFIGURE_IMAGE_DIR, "image.qcow2"),
        help="The path to the image that is to be configured",
    )
    parser.add_argument(
        "---image-qemu-socket-path",
        default=os.path.join(CONFIGURE_IMAGE_DIR, "qemu-monitor-socket"),
        help="The path to where the QEMU monitor socket should be placed which is used to send commands to the running image while it is being configured.",
    )
    parser.add_argument(
        "--config-user-data-path",
        default=os.path.join(CLOUD_CONFIG_DIR, "user-data"),
        help="The path to the cloud-init user-data configuration file",
    )
    parser.add_argument(
        "--config-meta-data-path",
        default=os.path.join(CLOUD_CONFIG_DIR, "meta-data"),
        help="The path to the cloud-init meta-data configuration file",
    )
    parser.add_argument(
        "--config-vendor-data-path",
        default=os.path.join(CLOUD_CONFIG_DIR, "vendor-data"),
        help="The path to the cloud-init vendor-data configuration file",
    )
    parser.add_argument(
        "--config-seed-output-path",
        default=os.path.join(IMAGE_CONFIG_DIR, "seed.img"),
        help="""The path to the cloud-init output seed image file that is generated
        based on the data defined in the user-data, meta-data, and vendor-data configs""",
    )
    # # https://qemu-project.gitlab.io/qemu/system/qemu-cpu-models.html
    parser.add_argument(
        "--qemu-cpu-model",
        default="host",
        help="The default cpu model for configuring the image",
    )

    args = parser.parse_args()

    image_path = args.image_input_path
    image_qemu_socket_path = args.image_qemu_socket_path
    user_data_path = args.config_user_data_path
    meta_data_path = args.config_meta_data_path
    vendor_data_path = args.config_vendor_data_path
    seed_output_path = args.config_seed_output_path
    qemu_cpu_model = args.qemu_cpu_model

    # Ensure that the image to configure exists
    if not exists(image_path):
        print(
            PATH_NOT_FOUND_ERROR_MSG.format(
                image_path, "the image to configured was not found"
            )
        )
        exit(PATH_NOT_FOUND_ERROR)

    # Ensure that the required output directories exists
    image_output_dir = os.path.dirname(image_path)
    image_config_dir = os.path.dirname(seed_output_path)

    for d in [image_output_dir, image_config_dir]:
        if not exists(d):
            created, msg = makedirs(d)
            if not created:
                print(PATH_CREATE_ERROR_MSG.format(d, msg))
                exit(PATH_CREATE_ERROR)

    generated_result, generated_msg = generate_image_configuration(
        user_data_path, meta_data_path, vendor_data_path, seed_output_path
    )
    if not generated_result:
        print(generated_msg)
        exit(generated_result)

    configured = configure_image(
        image_path, seed_output_path, image_qemu_socket_path, cpu_model=qemu_cpu_model
    )
    if not configured:
        print(CONFIGURE_IMAGE_ERROR_MSG.format(image_path, "failed to configure image"))
        exit(CONFIGURE_IMAGE_ERROR)

    reset = reset_image(image_path)
    if not reset:
        print(RESET_IMAGE_ERROR_MSG.format(image_path, "failed to reset image"))
        exit(RESET_IMAGE_ERROR)


if __name__ == "__main__":
    run_configure_image()
