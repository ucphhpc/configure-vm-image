import os
from gen_vm_image.common.codes import SUCCESS
from gen_vm_image.image import generate_image
from gen_vm_image.utils.net import download_file
from configure_vm_image.utils.io import join, makedirs, remove, exists, load
from configure_vm_image.common.defaults import CPU_ARCHITECTURE


TEST_IMAGE_NAME = "test_image"
TEST_IMAGE_FORMAT = "qcow2"
TEST_IMAGE_TEMPLATE_CONFIG = "configure-vm-template.xml.j2"
TEST_IMAGE_VERSION = "9.5-20241118.0"

INPUT_IMAGE_URL = f"https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base-{TEST_IMAGE_VERSION}.{CPU_ARCHITECTURE}.{TEST_IMAGE_FORMAT}"
INPUT_IMAGE_CHECKSUM_URL = f"https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base-{TEST_IMAGE_VERSION}.{CPU_ARCHITECTURE}.{TEST_IMAGE_FORMAT}.chksum.txt"


def extract_checksum_from_image_file(path):
    """Extract checksum, expects the format 'checksum (of first xxxxx bytes) relative_serverside_path'"""
    content = load(path)
    if not content:
        return False
    split_content = content.split(" ")
    checksum = split_content[0]
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
            # Test that the image can be configured
            success, msg = await generate_image(
                self.image_config["name"],
                self.image_config["size"],
                input=self.image_config["input"],
                input_checksum=checksum,
                input_checksum_type="sha256",
                input_checksum_read_bytes=int(checksum_byte_size),
                output_directory=self.image_config["output_directory"],
                output_format=self.image_config["output_format"],
            )
            assert success == SUCCESS
        assert exists(self.image)

        self.image_template_config = join(
            self.test_res_template_directory, TEST_IMAGE_TEMPLATE_CONFIG
        )
        assert exists(self.image_template_config)

    # Should be used by the non async function tearDownClass to ensure that
    # the following cleanup is done before the class is destroyed
    def tearDown(self):
        assert remove(self.test_tmp_directory, recursive=True)
