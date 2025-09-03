
OWNER:=rasmunk
PACKAGE_NAME=configure-vm-image
PACKAGE_NAME_FORMATTED=$(subst -,_,${PACKAGE_NAME})
CONFIGURE_IMAGES_DIR=configure-images
ARGS=

.PHONY: all
all: init install-dep install

.PHONY: init
init:
	mkdir -p ${CONFIGURE_IMAGES_DIR}

.PHONY: clean
clean:
	${MAKE} distclean
	${MAKE} venv-clean
	rm -fr ${CONFIGURE_IMAGES_DIR}
	rm -fr .env
	rm -fr .pytest_cache
	rm -fr tests/__pycache__

.PHONY: configure
configure: venv
	. ${VENV}/activate; ${PACKAGE_NAME} ${ARGS}

.PHONY: dist
dist: venv install-dist-dep
	$(VENV)/python -m build .

.PHONY: install-dist-dep
install-dist-dep: venv
	$(VENV)/pip install build

.PHONY: distclean
distclean:
	rm -fr dist build ${PACKAGE_NAME}.egg-info ${PACKAGE_NAME_FORMATTED}.egg-info

.PHONY: maintainer-clean
maintainer-clean:
	@echo 'This command is intended for maintainers to use; it'
	@echo 'deletes files that may need special tools to rebuild.'
	${MAKE} venv-clean
	${MAKE} clean

.PHONY: install
install: venv
	${VENV}/pip install .

.PHONY: uninstall
uninstall: venv
	${VENV}/pip uninstall -y ${PACKAGE_NAME}

.PHONY: install-dev
install-dev: venv
	${VENV}/pip install -r requirements-dev.txt

.PHONY: uninstall-dev
uninstall-dev: venv
	${VENV}/pip uninstall -y -r requirements-dev.txt

.PHONY: install-dep
install-dep: venv
	${VENV}/pip install -r requirements.txt

.PHONY: uninstall-dep
uninstall-dep: venv
	${VENV}/pip uninstall -r requirements.txt

.PHONY: uninstalltest
uninstalltest: venv
	${VENV}/pip uninstall -y -r tests/requirements.txt

.PHONY: installtest
installtest: venv
	${VENV}/pip install -r tests/requirements.txt

.PHONY: test
test:
	. ${VENV}/activate; pytest -s -v tests/

.PHONY: dockertest-clean
dockertest-clean:
	docker rmi -f ${OWNER}/configure-vm-image-tests

.PHONY: dockertest-build
dockertest-build:
# Use the docker image to test the installation
	docker build -f tests/Dockerfile -t ${OWNER}/configure-vm-image-tests .

.PHONY: dockertest-run
dockertest-run:
	docker run -it ${OWNER}/configure-vm-image-tests

include Makefile.venv