import json
import subprocess
import datetime


def __to_str__(o):
    if hasattr(o, "asdict"):
        return o.asdict()
    if isinstance(o, datetime.datetime):
        return o.__str__()
    if isinstance(o, bytes):
        return o.decode("utf-8")


def __format_output__(output, to_format="str"):
    if to_format == "str":
        if isinstance(output, bytes):
            return output.decode("utf-8")
        if isinstance(output, list):
            return ",".join(output)
        if isinstance(output, dict):
            formatted_output = {}
            for key, value in output.items():
                formatted_output[key] = str(value)
            return json.dumps(formatted_output)
        if isinstance(output, str):
            return output
    if to_format == "json":
        if is_json_string(output):
            return to_json(output)
        else:
            return f"Failed to convert output to json: {output}"
    return False


def __extract_results__(result):
    command_results = {"output": "", "error": "", "returncode": 1}
    if hasattr(result, "args"):
        command_results.update({"command": " ".join((getattr(result, "args")))})
    if hasattr(result, "returncode"):
        command_results.update({"returncode": getattr(result, "returncode")})
    if hasattr(result, "stderr"):
        command_results.update({"error": getattr(result, "stderr")})
    if hasattr(result, "stdout"):
        command_results.update({"output": getattr(result, "stdout")})
    if hasattr(result, "wait"):
        command_results.update({"wait": getattr(result, "wait")})
    if hasattr(result, "communicate"):
        command_results.update({"communicate": getattr(result, "communicate")})
    if hasattr(result, "kill"):
        command_results.update({"kill": getattr(result, "kill")})
    return command_results


def is_json_string(content):
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        print(content)
        return False
    return False


def to_json(content):
    return json.loads(content)


def run_popen(cmd, output_format="str", **run_kwargs):
    result = __extract_results__(subprocess.Popen(cmd, **run_kwargs))
    return __format_output__(result, to_format=output_format)


def check_call(cmd, output_format="str", **run_kwargs):
    result = __extract_results__(subprocess.check_call(cmd, **run_kwargs))
    return __format_output__(result, to_format=output_format)


def run(cmd, output_format="str", **run_kwargs):
    if not output_format:
        output_format = "str"
    return_values = {"output": "", "error": ""}
    try:
        raw_results = subprocess.run(cmd, **run_kwargs, capture_output=True)
    except Exception as e:
        return_values["error"] = f"Failed to run command: {cmd}, error: {e}"
        return False, return_values

    result = __extract_results__(raw_results)
    if result["error"]:
        formatted_error = __format_output__(result["error"], to_format=output_format)
        if formatted_error:
            return_values["error"] = formatted_error

    if result["output"]:
        formatted_output = __format_output__(result["output"], to_format=output_format)
        if formatted_output:
            return_values["output"] = formatted_output

    if result["returncode"] != 0:
        return False, return_values
    return True, return_values
