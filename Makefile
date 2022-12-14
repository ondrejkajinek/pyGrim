VERSION=$(shell python3 setup.py --version)

AUTHOR=$(shell python3 setup.py --author)
AUTHOR_EMAIL=$(shell python3 setup.py --author-email)
PACKAGE_NAME=$(shell python3 setup.py --name)
PY_VERSION=`python3 -c 'import sys; print(sys.version.split(" ",1)[0].rsplit(".",1)[0])'`

all: package

check:
	python3 setup.py check

package: build uploadPackage

build: check clean buildPip

buildPip:
	python3 setup.py sdist
	python3 setup.py sdist bdist_wheel


uploadPackage:
	twine upload --repository-url http://10.42.105.13/ dist/*

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

install:
	python3 setup.py install

linkItems:
	( \
		ln -sf `pwd`/pygrim /usr/local/lib/python${PY_VERSION}/dist-packages/pygrim
	)

unlinkItems:
	( \
		rm -f /usr/local/lib/python${PY_VERSION}/dist-packages/pygrim
	)

postinstall:
	( \
		python3 -m pip install -U pip &&\
		python3 -m pip install -r `pwd`/system-requirements.txt \
	)

link: linkItems postinstall

unlink: unlinkItems
