import os

import psutil
from gen_vm_image.common.codes import SUCCESS
from gen_vm_image.image import generate_image
from gen_vm_image.utils.net import download_file

from configure_vm_image.common.defaults import CPU_ARCHITECTURE
from configure_vm_image.utils.io import exists, join, load, makedirs, remove

TEST_IMAGE_NAME = "test_image"
TEST_IMAGE_FORMAT = "qcow2"
TEST_IMAGE_TEMPLATE_CONFIG = "configure-vm-template.xml.j2"
TEST_IMAGE_VERSION = "9.5-20241118.0"

INPUT_IMAGE_URL = f"https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base-{TEST_IMAGE_VERSION}.{CPU_ARCHITECTURE}.{TEST_IMAGE_FORMAT}"
INPUT_IMAGE_CHECKSUM_URL = f"https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base-{TEST_IMAGE_VERSION}.{CPU_ARCHITECTURE}.{TEST_IMAGE_FORMAT}.chksum.txt"


_1024_MIB_IN_BYTES = 1073741824


def get_memory_slice(available_memory_divisor=4, expected_units="mib"):
    available_bytes = psutil.virtual_memory().available
    memory_slice_in_bytes = int(available_bytes / available_memory_divisor)

    if memory_slice_in_bytes < _1024_MIB_IN_BYTES:
        # Don't use less than 1024MiB
        memory_slice_in_bytes = _1024_MIB_IN_BYTES

    # Transform to expected_units
    if expected_units == "kib":
        memory_slice = int(memory_slice_in_bytes / 1024)
    elif expected_units == "mib":
        memory_slice = int(memory_slice_in_bytes / (1024 * 1024))
    elif expected_units == "gib":
        memory_slice = int(memory_slice_in_bytes / (1024 * 1024 * 1024))
    else:
        raise ValueError(f"Unknown expected_units: {expected_units}")
    return memory_slice


def get_cpus_slice(core_count_divisor=2):
    available_cpus = os.cpu_count()
    cpus_slice = int(available_cpus / core_count_divisor)
    if cpus_slice < 2:
        cpus_slice = 2
    return cpus_slice


def extract_checksum_from_image_file(path):
    """Extract checksum, expects the format:
        'checksum (of first xxxxx bytes) relative_serverside_path'

    which will return the checksum and the byte size.

    Otherwise the function will expect that the entire file is used
    to calculate the checksum with the following format:
        'checksum relative_serverside_path'

    Which will return the checksum and None.
    """
    content = load(path)
    if not content:
        return False
    split_content = content.split(" ")
    checksum = split_content[0]
    if len(split_content) < 4:
        checksum_byte_size = None
    else:
        checksum_byte_size = split_content[3]
    return checksum, checksum_byte_size


class AsyncConfigureTestContext:
    def __init__(self):
        self.init_done = False

    async def setUp(self):
        if self.init_done:
            return

        # https://cloud.debian.org/images/cloud/bookworm/latest/input_path_image-genericcloud-amd64.qcow2
        # Download the test image for the path input test
        self.test_tmp_directory = os.path.realpath(join("tests", "tmp"))
        self.test_res_directory = os.path.realpath(join("tests", "res"))
        self.test_res_template_directory = os.path.realpath(
            join(self.test_res_directory, "templates")
        )
        if not exists(self.test_tmp_directory):
            assert makedirs(self.test_tmp_directory)

        self.image_config = {
            "name": TEST_IMAGE_NAME,
            # TODO, dynamically discover the size of the input image
            # This output size should not be less than what the original input disk image size
            "size": "10G",
            "input": INPUT_IMAGE_URL,
            "output_directory": self.test_tmp_directory,
            "output_format": TEST_IMAGE_FORMAT,
        }

        self.image = join(
            self.test_tmp_directory, "{}.{}".format(TEST_IMAGE_NAME, TEST_IMAGE_FORMAT)
        )
        if not exists(self.image):
            checksum_file_path = join(
                self.test_tmp_directory, f"{TEST_IMAGE_NAME}.checksum"
            )
            downloaded, response = await download_file(
                INPUT_IMAGE_CHECKSUM_URL, checksum_file_path
            )
            assert downloaded
            assert exists(checksum_file_path)
            checksum, checksum_byte_size = extract_checksum_from_image_file(
                checksum_file_path
            )
            if checksum_byte_size is not None:
                checksum_byte_size = int(checksum_byte_size)

            # Test that the image can be configured
            success, msg = await generate_image(
                self.image_config["name"],
                self.image_config["size"],
                input=self.image_config["input"],
                input_checksum=checksum,
                input_checksum_type="sha256",
                input_checksum_read_bytes=checksum_byte_size,
                output_directory=self.image_config["output_directory"],
                output_format=self.image_config["output_format"],
            )
            assert success == SUCCESS
        assert exists(self.image)

        self.image_template_config = join(
            self.test_res_template_directory, TEST_IMAGE_TEMPLATE_CONFIG
        )
        assert exists(self.image_template_config)

        self.test_num_cpus = str(get_cpus_slice())
        memory_unit = "mib"
        self.test_memory_size = "{}{}".format(
            get_memory_slice(expected_units=memory_unit), memory_unit
        )

        # https://libguestfs.org/guestfs-internals.1.html
        # if we don't set this, the libguestfs will attempt to write to /var/tmp/.guestfs-<UID>
        # which we might not have write permissions to. Furthermore we should keep all test related data in the test_tmp_directory
        os.environ["TMPDIR"] = self.test_tmp_directory

    # Should be used by the non async function tearDownClass to ensure that
    # the following cleanup is done before the class is destroyed
    def tearDown(self):
        assert remove(self.test_tmp_directory, recursive=True)
