.PHONY: help all clean build build-all maintainer-clean install-dep uninstall-dep
.PHONY: installtest uninstalltest test test-all

OWNER:=rasmunk
PACKAGE_NAME=configure-vm-image
PACKAGE_NAME_FORMATTED=$(subst -,_,${PACKAGE_NAME})
CONFIGURE_IMAGES_DIR=configure-images
ARGS=

all: init install-dep install

init:
	mkdir ${CONFIGURE_IMAGES_DIR}

clean:
	${MAKE} distclean
	${MAKE} venv-clean
	rm -fr ${CONFIGURE_IMAGES_DIR}
	rm -fr .env
	rm -fr .pytest_cache
	rm -fr tests/__pycache__

configure: venv
	. ${VENV}/activate; configure-vm-image ${ARGS}

dist: venv
	${VENV}/python setup.py sdist bdist_wheel

distclean:
	rm -fr dist build ${PACKAGE_NAME}.egg-info ${PACKAGE_NAME_FORMATTED}.egg-info

maintainer-clean:
	@echo 'This command is intended for maintainers to use; it'
	@echo 'deletes files that may need special tools to rebuild.'
	${MAKE} venv-clean
	${MAKE} clean

install: venv
	${VENV}/pip install .

uninstall: venv
	${VENV}/pip uninstall -y configure-vm-image

install-dev: venv
	${VENV}/pip install -r requirements-dev.txt

install-dep: venv
	${VENV}/pip install -r requirements.txt

uninstall-dep: venv
	${VENV}/pip uninstall -r requirements.txt

uninstalltest: venv
	${VENV}/pip uninstall -y -r tests/requirements.txt

installtest: venv
	${VENV}/pip install -r tests/requirements.txt

test:
# TODO, add tests

dockertest-clean:
	docker rmi -f ${OWNER}/configure-vm-image-tests

dockertest-build:
# Use the docker image to test the installation
	docker build -f tests/Dockerfile -t ${OWNER}/configure-vm-image-tests .

dockertest-run:
	docker run -it ${OWNER}/configure-vm-image-tests

include Makefile.venv