import unittest
import os
import random
from configure_vm_image.utils.io import exists, join, copy, remove
from configure_vm_image.cli.configure_image import main
from configure_vm_image.common.defaults import (
    CPU_ARCHITECTURE,
    CONFIGURE_VM_MACHINE,
    CONFIGURE_VM_MEMORY,
    CONFIGURE_VM_VCPUS,
)
from configure_vm_image.common.codes import SUCCESS
from .context import AsyncConfigureTestContext


def cli_action(*args):
    return_code = None
    try:
        return_code = main(args)
    except SystemExit as e:
        return_code = e.code
    return return_code


class TestCLIConfigurer(unittest.IsolatedAsyncioTestCase):
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

    def test_configurer_cli_with_default_template(self):
        args = [
            self.image_to_configure,
            "--config-user-data-path",
            join(self.cloud_init_directory, "user-data"),
            "--config-network-config-path",
            join(self.cloud_init_directory, "network-config"),
            "--cloud-init-iso-output-path",
            join(self.cloud_init_output_directory, f"{self.seed}-cidata.iso"),
            "--configure-vm-name",
            self.configure_vm_name,
            "--configure-vm-log-path",
            self.configure_vm_log_path,
            "--configure-vm-template-path",
            self.context.image_template_config,
        ]
        return_code = cli_action(*args)
        self.assertEqual(return_code, SUCCESS)

    def test_configurer_cli_with_set_template_values(self):
        configure_vm_template_values = ",".join(
            [
                f"memory_size={CONFIGURE_VM_MEMORY}",
                f"num_vcpus={CONFIGURE_VM_VCPUS}",
                f"cpu_architecture={CPU_ARCHITECTURE}",
                f"machine={CONFIGURE_VM_MACHINE}",
            ]
        )

        args = [
            self.image_to_configure,
            "--config-user-data-path",
            join(self.cloud_init_directory, "user-data"),
            "--config-network-config-path",
            join(self.cloud_init_directory, "network-config"),
            "--cloud-init-iso-output-path",
            join(self.cloud_init_output_directory, f"{self.seed}-cidata.iso"),
            "--configure-vm-name",
            self.configure_vm_name,
            "--configure-vm-log-path",
            self.configure_vm_log_path,
            "--configure-vm-template-values",
            configure_vm_template_values,
            "--configure-vm-template-path",
            self.context.image_template_config,
        ]
        return_code = cli_action(*args)
        self.assertEqual(return_code, SUCCESS)
