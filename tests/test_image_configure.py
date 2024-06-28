import unittest
from gen_vm_image.cli.build_image import create_image


class TestImageConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup an image that can be configured
        cls.image_config = {
            "name": "test-image",
            "version": "1.0",
            "size": "20G",
            "format": "qcow2",
        }

    @classmethod
    def tearDownClass(cls):
        pass

    def test_config_image(self):
        # Test that the image can be configured
        result, msg = create_image(
            self.image_config["name"],
            self.image_config["version"],
            self.image_config["size"],
            image_format=self.image_config["format"],
        )
        self.assertNotIsInstance(result, int)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["returncode"], "0")
        self.assertIsNone(msg)
