import os

PACKAGE_NAME = "configure-vm-image"
REPO_NAME = "configure-vm-image"
GOCD_GROUP = "bare_metal_vm_image"
GOCD_TEMPLATE = "bare_metal_vm_image"
GOCD_FORMAT_VERSION = 10
GO_REVISION_COMMIT_VAR = "GO_REVISION_SIF_VM_IMAGES"
CLOUD_INIT_DIR = "cloud-init"
CONFIGURE_IMAGE_TMP_DIR = os.path.join(os.sep, "tmp", "configure-vm-image")
VM_DISK_DIR = "vmdisks"
TMP_DIR = "tmp"
RES_DIR = "res"
CONFIGURE_ARGUMENT = "configure_argument"
