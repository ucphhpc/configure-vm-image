import asyncio
import argparse
import inspect
import sys
import json
from configure_vm_image._version import __version__
from configure_vm_image.common.defaults import CONFIGURE_ARGUMENT
from configure_vm_image.common.utils import to_str, error_print
from configure_vm_image.common.codes import (
    SUCCESS,
    JSON_DUMP_ERROR,
    JSON_DUMP_ERROR_MSG,
)
from configure_vm_image.cli.helpers import (
    extract_arguments,
    strip_argument_group_prefix,
)

SCRIPT_NAME = __file__


def import_from_module(module_path, module_name, func_name):
    module = __import__(module_path, fromlist=[module_name])
    return getattr(module, func_name)


def add_cli_operations(
    parser,
    operation,
    module_cli_input_group_prefix="configure_vm_image.cli.input_groups",
    module_operation_prefix="configure_vm_image.cli.operations",
):
    operation_input_groups_func = import_from_module(
        "{}.{}".format(module_cli_input_group_prefix, operation),
        "{}".format(operation),
        "{}_groups".format(operation),
    )

    argument_groups = operation_input_groups_func(parser)

    parser.set_defaults(
        func=cli_exec,
        module_path="{}.{}".format(module_operation_prefix, operation),
        module_name="{}".format(operation),
        func_name="{}_operation".format(operation),
        argument_groups=argument_groups,
    )


def cli_exec(arguments):
    # Actions determines which function to execute
    module_path = arguments.pop("module_path")
    module_name = arguments.pop("module_name")
    func_name = arguments.pop("func_name")

    if "positional_arguments" in arguments:
        positional_arguments = arguments.pop("positional_arguments")
    else:
        positional_arguments = []

    if "argument_groups" in arguments:
        argument_groups = arguments.pop("argument_groups")
    else:
        argument_groups = []

    func = import_from_module(module_path, module_name, func_name)
    if not func:
        return False, {}

    action_kwargs, _ = extract_arguments(arguments, argument_groups)
    action_kwargs = strip_argument_group_prefix(action_kwargs, argument_groups)

    action_args = positional_arguments
    if inspect.iscoroutinefunction(func):
        return asyncio.run(func(*action_args, **action_kwargs))
    return func(*action_args, **action_kwargs)


def add_base_cli_operations(parser):
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=__version__,
        help="Print the version of the program",
    )


def main(args):
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Add the basic CLI functions
    add_base_cli_operations(parser)
    # Add the configure image CLI
    add_cli_operations(parser, "configure")

    parsed_args = parser.parse_args(args)
    # Convert to a dictionary
    arguments = vars(parsed_args)

    if "func" not in arguments:
        raise ValueError("Missing function to execute in prepared arguments")

    func = arguments.pop("func")
    return_code, result_dict = func(arguments)

    response = {}
    if return_code == SUCCESS:
        response["status"] = "success"
    else:
        response["status"] = "failed"
    if arguments.get("{}_verbose".format(CONFIGURE_ARGUMENT), False):
        response["outputs"] = result_dict.get("verbose_outputs", [])
    response["msg"] = result_dict.get("msg", "")
    response["return_code"] = return_code

    try:
        output = json.dumps(response, indent=4, sort_keys=True, default=to_str)
    except Exception as err:
        error_print(JSON_DUMP_ERROR_MSG.format(err))
        return JSON_DUMP_ERROR
    if return_code == SUCCESS:
        print(output)
    else:
        error_print(output)
    return return_code


def cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
