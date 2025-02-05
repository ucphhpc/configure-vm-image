import unittest
import os
import random
from configure_vm_image.cli.configure_image import configure_vm_image
from configure_vm_image.utils.io import join, copy, exists, remove
from configure_vm_image.common.codes import SUCCESS
from .context import AsyncConfigureTestContext


class AsyncTestImageConfiguration(unittest.IsolatedAsyncioTestCase):
    context = AsyncConfigureTestContext()

    async def asyncSetUp(self):
        await self.context.setUp()

        self.seed = str(random.random())[2:10]
        self.assertTrue(exists(self.context.image))

        self.configure_vm_name = f"configure-vm-test-{self.seed}"
        self.configure_vm_log_path = os.path.realpath(
            f"{join(self.context.test_tmp_directory, self.configure_vm_name)}.log"
        )
        self.image_to_configure = os.path.realpath(f"{os.path.splitext(self.context.image)[0]}-{self.seed}.{self.context.image_config['output_format']}")

        self.assertTrue(copy(self.context.image, self.image_to_configure))
        self.assertTrue(exists(self.image_to_configure))

    async def asyncTearDown(self):
        # Cleanup the test images
        self.assertTrue(remove(self.image_to_configure))

    @classmethod
    def tearDownClass(cls):
        cls.context.tearDown()

    async def test_basic_configure(self):
        cloud_init_directory = join(self.context.test_res_directory, "test-cloud-init")
        return_code, msg = await configure_vm_image(
            self.image_to_configure,
            configure_vm_name=self.configure_vm_name,
            configure_vm_vcpus="4",
            configure_vm_memory="4096MiB",
            configure_vm_log_path=self.configure_vm_log_path,
            meta_data_path=join(cloud_init_directory, "meta-data"),
            network_config_path=join(cloud_init_directory, "network-config"),
            user_data_path=join(cloud_init_directory, "user-data"),
            vendor_data_path=join(cloud_init_directory, "vendor-data"),
            cloud_init_iso_output_path=join(cloud_init_directory, "{self.seed}-cidata.iso"),
            verbose=True,
            verbose_reset=True
        )
        self.assertEqual(return_code, SUCCESS)
        self.assertIsNotNone(msg)
