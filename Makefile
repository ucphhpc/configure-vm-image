.PHONY: help all clean build build-all maintainer-clean install-dep uninstall-dep
.PHONY: installcheck uninstallcheck test test-all

OWNER:=rasmunk
PACKAGE_NAME=configure-vm-image
PACKAGE_NAME_FORMATTED=$(subst -,_,$(PACKAGE_NAME))
BUILD_ARGS=
CONFIGURE_ARGS=

all: venv install-dep install configure

clean:
	$(MAKE) distclean
	$(MAKE) venv-clean
	rm -fr .env
	rm -fr .pytest_cache
	rm -fr tests/__pycache__

configure:
	. $(VENV)/activate; configure-vm-image $(CONFIGURE_ARGS)

dist:
	$(VENV)/python setup.py sdist bdist_wheel

distclean:
	rm -fr dist build $(PACKAGE_NAME).egg-info $(PACKAGE_NAME_FORMATTED).egg-info

maintainer-clean:
	@echo 'This command is intended for maintainers to use; it'
	@echo 'deletes files that may need special tools to rebuild.'
	$(MAKE) venv-clean
	$(MAKE) clean

install:
	$(VENV)/pip install .

uninstall:
	$(VENV)/pip uninstall -y configure-vm-image

install-dev:
	$(VENV)/pip install -r requirements-dev.txt

install-dep:
	$(VENV)/pip install -r requirements.txt

uninstall-dep:
	$(VENV)/pip uninstall -r requirements.txt

uninstallcheck:
	$(VENV)/pip uninstall -y -r tests/requirements.txt

installcheck:
	$(VENV)/pip install -r tests/requirements.txt

check:
# TODO, add checks

dockercheck-clean:
	docker rmi -f $(OWNER)/configure-vm-image-tests

dockercheck-build:
# Use the docker image to test the installation
	docker build -f tests/Dockerfile -t $(OWNER)/configure-vm-image-tests .

dockercheck-run:
	docker run -it $(OWNER)/configure-vm-image-tests


include Makefile.venv
