from configure_vm_image.cli.parsers.configure import configure_group
from configure_vm_image.common.defaults import CONFIGURE_ARGUMENT


def configure_groups(parser):
    configure_group(parser)

    argument_groups = [CONFIGURE_ARGUMENT]
    return argument_groups
