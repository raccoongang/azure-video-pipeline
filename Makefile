SHELL := /bin/bash

.PHONY=all,quality,test


all: quality test ## Run quality checks and tests

quality: ## Run Python code style checks
	@echo Checking python code style...
	python2.7 -m flake8 azure_video_pipeline

test: ## Run Python tests
	@echo Running python unit tests...
	nosetests azure_video_pipeline.tests.unit --with-coverage --cover-package=azure_video_pipeline

install-dev: ## Install package using pip to leverage pip's cache and shorten CI build time
	pip install --process-dependency-links -e .

install-test: ## Install dependencies required to run tests
	@echo [re]installing python testing requirements...
	-pip install -Ur requirements_test.txt


clean: ## Clean working directory
	-find . -name *.pyc -delete

help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
