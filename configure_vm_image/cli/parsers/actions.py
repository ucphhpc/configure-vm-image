import argparse

from configure_vm_image.common.utils import transform_str_to_dict


class PositionalArgumentsAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "positional_arguments") or not getattr(
            namespace, "positional_arguments"
        ):
            setattr(namespace, "positional_arguments", [values])
        else:
            getattr(namespace, "positional_arguments").append(values)


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        key_value_dict = transform_str_to_dict(values)
        setattr(namespace, self.dest, key_value_dict)
