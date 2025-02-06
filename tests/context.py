import os
import platform
from gen_vm_image.common.codes import SUCCESS
from gen_vm_image.image import generate_image
from gen_vm_image.utils.net import download_file
from configure_vm_image.utils.io import join, makedirs, remove, exists, load


CPU_ARCHITECTURE = platform.machine()
TEST_IMAGE_NAME = "test_image"
TEST_IMAGE_FORMAT = "qcow2"
INPUT_IMAGE_URL = "https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base.latest.{}.qcow2".format(
    CPU_ARCHITECTURE
)
INPUT_IMAGE_CHECKSUM_URL = "https://sid.erda.dk/share_redirect/B0AM7a5lpC/Rocky-9-GenericCloud-Base.latest.{}.qcow2.chksum.txt".format(
    CPU_ARCHITECTURE
)


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
        if not exists(self.test_tmp_directory):
            assert makedirs(self.test_tmp_directory)

        self.image_config = {
            "name": TEST_IMAGE_NAME,
            "size": "3G",
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

    # Should be used by the non async function tearDownClass to ensure that
    # the following cleanup is done before the class is destroyed
    def tearDown(self):
        assert remove(self.test_tmp_directory, recursive=True)
