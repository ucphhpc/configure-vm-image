from configure_vm_image.configure import configure_vm_image


async def configure_operation(*args, **kwargs):
    return await configure_vm_image(*args, **kwargs)
