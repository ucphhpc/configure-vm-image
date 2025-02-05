def strip_argument_prefix(arguments, prefix=""):
    return {k.replace(prefix, ""): v for k, v in arguments.items()}


def get_arguments(arguments, startswith=""):
    return {k: v for k, v in arguments.items() if k.startswith(startswith)}


def extract_arguments(arguments, argument_groups):
    found_kwargs, remaining_kwargs = {}, {}
    for argument_group in argument_groups:
        group_args = get_arguments(arguments, argument_group.lower())
        found_kwargs.update(group_args)
    remaining_kwargs = {
        k: v for k, v in arguments.items() if k not in found_kwargs and v
    }
    return found_kwargs, remaining_kwargs


def strip_argument_group_prefix(arguments, argument_groups):
    args = {}
    for argument_group in argument_groups:
        group_arguments = get_arguments(arguments, argument_group.lower())
        args.update(
            strip_argument_prefix(group_arguments, argument_group.lower() + "_")
        )
    return args
