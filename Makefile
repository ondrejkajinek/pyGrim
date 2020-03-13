VERSION=$(shell python3 setup.py --version)
AUTHOR=$(shell python3 setup.py --author)
AUTHOR_EMAIL=$(shell python3 setup.py --author-email)
PACKAGE_NAME=$(shell python3 setup.py --name)

VERSIONED_NAME=${PACKAGE_NAME}-${VERSION}
ARCHIVE=${VERSIONED_NAME}.tar.gz
ORIG_ARCHIVE=${PACKAGE_NAME}_${VERSION}.orig.tar.gz
FULL_PKG_NAME=${PACKAGE_NAME}_${VERSION}_all.deb
PACKAGES_REMOTE_DIR="/var/aptly/packages/"
ENV=DEBFULLNAME="$(AUTHOR)" DEBEMAIL=$(AUTHOR_EMAIL) EDITOR=vim

PY_VERSION=`python3 -c 'import sys; print(sys.version.split(" ",1)[0].rsplit(".",1)[0])'`

all: deb

prePackCheck:
	( \
		apt-get install devscripts fakeroot python-all\
	)

deb: prePackCheck clean buildDeb

gitCheck:
	python3 setup.py check

buildDeb: gitCheck sdist
	mkdir build \
	&& cp dist/${ARCHIVE} build/${ORIG_ARCHIVE} \
	&& tar -xf build/${ORIG_ARCHIVE} -C build/ \
	&& python3 setup.py changelog \
	&& cp -r debian build/${VERSIONED_NAME} \
	&& cd build/${VERSIONED_NAME} \
	&& $(ENV) debuild -us -uc

pkg: deb

debtest: deb
	python3 setup.py create_tag \
	&& scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} \
	&& ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie \
	&& scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} \
	&& ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} stretch

debbuster: deb
	python3 setup.py create_tag \
	&& scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} \
	&& ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} buster

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

sdist: gitCheck
	python3 setup.py sdist

install:
	python3 setup.py install

linkItems:
	ln -sf `pwd`/pygrim2 /usr/local/lib/python${PY_VERSION}/dist-packages/pygrim2

unlinkItems:
	rm -f /usr/local/lib/python${PY_VERSION}/dist-packages/pygrim2

postinstall:
	bash `pwd`/debian/postinst

installPackages:
	apt-get install python-dev

link: linkItems installPackages postinstall

unlink: unlinkItems
