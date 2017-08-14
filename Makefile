VERSION=$(shell python setup.py --version)
AUTHOR=$(shell python setup.py --author)
AUTHOR_EMAIL=$(shell python setup.py --author-email)
PACKAGE_NAME=$(shell python setup.py --name)

VERSIONED_NAME=${PACKAGE_NAME}-${VERSION}
ARCHIVE=${VERSIONED_NAME}.tar.gz
ORIG_ARCHIVE=${PACKAGE_NAME}_${VERSION}.orig.tar.gz
FULL_PKG_NAME=${PACKAGE_NAME}_${VERSION}_all.deb
PACKAGES_REMOTE_DIR="/var/aptly/packages/"
ENV=DEBFULLNAME="$(AUTHOR)" DEBEMAIL=$(AUTHOR_EMAIL) EDITOR=vim

PY_VERSION=`python -c 'import sys; print(sys.version.split(" ",1)[0].rsplit(".",1)[0])'`

all: deb

prePackCheck:
	( \
		apt-get install devscripts fakeroot python-all\
	)

deb: prePackCheck clean buildDeb

gitCheck:
	python setup.py check

buildDeb: sdist gitCheck
	mkdir build \
	&& cp dist/${ARCHIVE} build/${ORIG_ARCHIVE} \
	&& tar -xf build/${ORIG_ARCHIVE} -C build/ \
	&& python setup.py changelog \
	&& cp -r debian build/${VERSIONED_NAME} \
	&& cd build/${VERSIONED_NAME} \
	&& $(ENV) debuild -us -uc

pkg: deb

debtest: deb
	python setup.py create_tag \
	&& scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} \
	&& ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie

debprod: deb
	python setup.py create_tag \
	&& scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} \
	&& ssh aptly@debian.ats bash pkg-to-stable ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

sdist:
	python setup.py sdist

install:
	python setup.py install

linkItems:
	( \
		ln -sf `pwd`/pygrim /usr/local/lib/python${PY_VERSION}/dist-packages/pygrim  \
    )

postinstall:
	( \
    	bash `pwd`/debian/postinst \
	)

installPackages:
	( \
		apt-get install python-dev \
	)

link: linkItems installPackages postinstall
