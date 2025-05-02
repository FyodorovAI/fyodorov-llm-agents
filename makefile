include .env

# Set up virtual environment
venv:
	python3 -m venv venv

# Publish the package to GitHub Packages
publish:
	export API_TOKEN=${API_TOKEN} && echo 'token: ${API_TOKEN}' && python3 -m twine upload --username __token__ --password ${API_TOKEN} --verbose dist/*

# Install requirements from requirements.txt
install:
	pip install -r requirements.txt

build:
	rm -rf ./dist
	python3 -m build

release: build publish

lint:
	ruff check src/fyodorov_llm_agents/

format:
	ruff format src/fyodorov_llm_agents/