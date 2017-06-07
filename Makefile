VERSION=$(shell python setup.py version)
AUTHOR=$(shell python setup.py author)
AUTHOR_EMAIL=$(shell python setup.py author_email)
PACKAGE_NAME=$(shell python setup.py name)
DEB_PACKAGE_NAME=$(PACKAGE_NAME)
ARCHIVE=$(PACKAGE_NAME)-$(VERSION).tar.gz
# REV=$(shell svn info |grep Revision:)
# CVS=GIT

ENV=DEBFULLNAME="$(AUTHOR)" DEBEMAIL=$(AUTHOR_EMAIL) EDITOR=vim

DEBIAN_ORIG_ARCHIVE=${DEB_PACKAGE_NAME}_${VERSION}.orig.tar.gz
ORIG_ARCHIVE=${PACKAGE_NAME}_${VERSION}.orig.tar.gz

FULL_PKG_NAME=${PACKAGE_NAME}_${VERSION}_all.deb
PACKAGES_REMOTE_DIR="/var/aptly/packages/"

PY_VERSION=`python -c 'import sys; print(sys.version.split(" ",1)[0].rsplit(".",1)[0])'`

all: pkg

prePackCheck:
	( \
		apt-get install devscripts fakeroot python-all\
	)

pkg: prePackCheck clean buildDeb

runGit:
	python setup.py check

buildDeb: runGit
	python setup.py sdist
	mkdir build
	cp dist/${ARCHIVE} build/${ORIG_ARCHIVE}
	cd build && tar -xf ${ORIG_ARCHIVE}
	cp -r debian build/${PACKAGE_NAME}-${VERSION}
	cd build/${PACKAGE_NAME}-${VERSION} && \
		$(ENV) debuild -us -uc


deb: pkg
	scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} && \
		ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie && \
		git push

debtest: deb

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

sdist:
	./setup.py sdist

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
