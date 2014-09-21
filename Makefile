.PHONY: default isvirtualenv

default:
	@echo "test, testpdb, testcovweb, style, lint"

isvirtualenv:
	@if [ -z "$(VIRTUAL_ENV)" ]; then echo "ERROR: Not in a virtualenv." 1>&2; exit 1; fi

style:
	flake8 --max-line-length=120 --statistics .

lint:
	pylint --max-line-length=120 .

test:
	py.test --cov-report term-missing --cov . tests

testpdb:
	py.test --pdb tests

testcovweb:
	py.test --cov-report html --cov . tests
	open htmlcov/index.html

pipinstall: isvirtualenv
	pip install -r requirements.txt
