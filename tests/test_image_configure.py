import unittest
import os
import random
from configure_vm_image.cli.configure_image import configure_vm_image
from configure_vm_image.utils.io import join, copy, exists, remove
from configure_vm_image.common.codes import SUCCESS
from .context import AsyncConfigureTestContext, CPU_ARCHITECTURE


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

        self.assertTrue(copy(self.context.image, self.image_to_configure))
        self.assertTrue(exists(self.image_to_configure))

        self.configure_vm_memory = "1024MiB"
        self.configure_vm_vcpus = "1"
        self.configure_vm_cpu_arch = CPU_ARCHITECTURE
        self.configure_vm_machine = "pc"
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
        cloud_init_directory = join(self.context.test_res_directory, "test-cloud-init")
        cloud_init_output_directory = join(
            self.context.test_tmp_directory, "cloud-init"
        )

        configure_vm_template_values = [
            f"memory_size={self.configure_vm_memory}",
            f"num_vcpus={self.configure_vm_vcpus}",
            f"cpu_architecture={self.configure_vm_cpu_arch}",
            f"machine={self.configure_vm_machine}",
        ]

        return_code, msg = await configure_vm_image(
            self.image_to_configure,
            network_config_path=join(cloud_init_directory, "network-config"),
            user_data_path=join(cloud_init_directory, "user-data"),
            cloud_init_iso_output_path=join(
                cloud_init_output_directory, f"{self.seed}-cidata.iso"
            ),
            configure_vm_name=self.configure_vm_name,
            configure_vm_log_path=self.configure_vm_log_path,
            configure_vm_template_path=self.context.image_template_config,
            configure_vm_template_values=configure_vm_template_values,
            verbose=True,
            verbose_reset=True,
        )
        self.assertEqual(return_code, SUCCESS)
        self.assertIsNotNone(msg)
