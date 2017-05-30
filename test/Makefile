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


all: deb

prePackCheck:
	( \
		apt-get install devscripts fakeroot python-all\
	)

deb: prePackCheck clean buildDeb

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

pkg: deb

debtest: deb
	scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} && \
		ssh aptly@debian.ats bash pkg-to-testing ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie

debprod: deb
	scp build/${FULL_PKG_NAME} debian.ats:${PACKAGES_REMOTE_DIR} && \
		ssh aptly@debian.ats bash pkg-to-stable ${PACKAGES_REMOTE_DIR}${FULL_PKG_NAME} jessie

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

sdist:
	./setup.py sdist

install:
	python setup.py install

makeStructure:
	( \
    	mkdir -p /www/${PACKAGE_NAME}/run \
        && mkdir -p /www/${PACKAGE_NAME}/log \
        && mkdir -p /www/${PACKAGE_NAME}/bin \
    )
installPackages:
	( \
		apt-get install python-dev\
	)

linkItems: installPackages makeStructure
	( \
		ln -sf `pwd`/conf /www/${PACKAGE_NAME}/  \
		&& ln -sf `pwd`/server /www/${PACKAGE_NAME}/  \
		&& ln -sf `pwd`/templates /www/${PACKAGE_NAME}/  \
        && ln -sf `pwd`/etc/init.d/* /etc/init.d/ \
    )

repairRights:
	( \
    	chown -R www-data:www-data /www/${PACKAGE_NAME} \
        && chmod +x etc/init.d/* \
    )

postinstall:
	( \
    	bash `pwd`/debian/postinst \
    )

link: linkItems repairRights postinstall
