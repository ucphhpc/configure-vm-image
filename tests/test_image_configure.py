import unittest
import os
import random
from configure_vm_image.configure import configure_vm_image
from configure_vm_image.utils.io import join, copy, exists, remove
from configure_vm_image.common.defaults import (
    CPU_ARCHITECTURE,
    CONFIGURE_VM_MACHINE,
    CONFIGURE_VM_MEMORY,
    CONFIGURE_VM_VCPUS,
)
from configure_vm_image.common.codes import SUCCESS
from .context import AsyncConfigureTestContext


class AsyncTestImageConfiguration(unittest.IsolatedAsyncioTestCase):
    context = AsyncConfigureTestContext()

    async def asyncSetUp(self):
        await self.context.setUp()

        self.seed = str(random.random())[2:10]
        self.assertTrue(exists(self.context.image))

        self.configure_vm_name = f"configure-vm-test-{self.seed}"
        self.image_to_configure = os.path.realpath(
            f"{os.path.splitext(self.context.image)[0]}-{self.seed}.{self.context.image_config['output_format']}"
        )
        self.cloud_init_directory = join(
            self.context.test_res_directory, "test-cloud-init"
        )
        self.cloud_init_output_directory = join(
            self.context.test_tmp_directory, "cloud-init"
        )

        self.assertTrue(copy(self.context.image, self.image_to_configure))
        self.assertTrue(exists(self.image_to_configure))

        self.configure_vm_log_path = os.path.realpath(
            f"{join(self.context.test_tmp_directory, self.configure_vm_name)}.log"
        )

    async def asyncTearDown(self):
        # Cleanup the test images
        self.assertTrue(remove(self.image_to_configure))

    @classmethod
    def tearDownClass(cls):
        cls.context.tearDown()

    async def test_basic_configure(self):
        return_code, msg = await configure_vm_image(
            self.image_to_configure,
            network_config_path=join(self.cloud_init_directory, "network-config"),
            user_data_path=join(self.cloud_init_directory, "user-data"),
            cloud_init_iso_output_path=join(
                self.cloud_init_output_directory, f"{self.seed}-cidata.iso"
            ),
            configure_vm_name=self.configure_vm_name,
            configure_vm_log_path=self.configure_vm_log_path,
            configure_vm_template_path=self.context.image_template_config,
            verbose=True,
        )
        self.assertEqual(return_code, SUCCESS)
        self.assertIsNotNone(msg)

    async def test_basic_configure_with_template_values(self):
        configure_vm_template_values = {
            "memory_size": CONFIGURE_VM_MEMORY,
            "num_vcpus": CONFIGURE_VM_VCPUS,
            "cpu_architecture": CPU_ARCHITECTURE,
            "machine": CONFIGURE_VM_MACHINE,
        }

        return_code, msg = await configure_vm_image(
            self.image_to_configure,
            network_config_path=join(self.cloud_init_directory, "network-config"),
            user_data_path=join(self.cloud_init_directory, "user-data"),
            cloud_init_iso_output_path=join(
                self.cloud_init_output_directory, f"{self.seed}-cidata.iso"
            ),
            configure_vm_name=self.configure_vm_name,
            configure_vm_log_path=self.configure_vm_log_path,
            configure_vm_template_path=self.context.image_template_config,
            configure_vm_template_values=configure_vm_template_values,
            verbose=True,
        )
        self.assertEqual(return_code, SUCCESS)
        self.assertIsNotNone(msg)
