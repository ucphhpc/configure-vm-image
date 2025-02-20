from configure_vm_image.configure import configure_vm_image


async def configure_operation(*args, **kwargs):
    return await configure_vm_image(*args, **kwargs)

    # return_code, result_dict = configure_vm_image(
    #     expand_path(args.image_path),
    #     image_format=args.image_format,
    #     user_data_path=expand_path(args.config_user_data_path),
    #     meta_data_path=expand_path(args.config_meta_data_path),
    #     vendor_data_path=expand_path(args.config_vendor_data_path),
    #     network_config_path=expand_path(args.config_network_config_path),
    #     cloud_init_iso_output_path=expand_path(args.cloud_init_iso_output_path),
    #     configure_vm_log_path=expand_path(args.configure_vm_log_path),
    #     configure_vm_template_path=expand_path(args.configure_vm_template_path),
    #     configure_vm_template_values=args.configure_vm_template_values,
    #     reset_operations=args.reset_operations,
    #     verbose=args.verbose,
    #     verbose_reset=args.verbose_reset,
    # )
