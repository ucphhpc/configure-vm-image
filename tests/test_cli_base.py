import unittest
from configure_vm_image.common.codes import SUCCESS
from configure_vm_image.cli.configure_image import main


class TestCLIBase(unittest.TestCase):

    def test_cli_help(self):
        return_code = None
        try:
            return_code = main(["--help"])
        except SystemExit as e:
            return_code = e.code
        self.assertEqual(return_code, SUCCESS)

    def test_cli_version(self):
        return_code = None
        try:
            return_code = main(["--version"])
        except SystemExit as e:
            return_code = e.code
        self.assertEqual(return_code, SUCCESS)
