import os
from gen_vm_image.common.codes import SUCCESS
from gen_vm_image.image import generate_image
from configure_vm_image.utils.io import join, makedirs, remove, exists


TEST_IMAGE_NAME = "test_image"
TEST_IMAGE_FORMAT = "qcow2"
INPUT_IMAGE_URL = "https://dl.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2"


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
            "size": "1G",
            "input": INPUT_IMAGE_URL,
            "output_directory": self.test_tmp_directory,
            "output_format": TEST_IMAGE_FORMAT,
        }

        self.image = join(
            self.test_tmp_directory, "{}.{}".format(TEST_IMAGE_NAME, TEST_IMAGE_FORMAT)
        )

        if not exists(self.image):
            # Test that the image can be configured
            success, msg = await generate_image(
                self.image_config["name"],
                self.image_config["size"],
                output_directory=self.image_config["output_directory"],
                output_format=self.image_config["output_format"],
            )
            assert success == SUCCESS
        assert exists(self.image)

    # Should be used by the non async function tearDownClass to ensure that
    # the following cleanup is done before the class is destroyed
    def tearDown(self):
        pass
        # assert remove(self.test_tmp_directory, recursive=True)
