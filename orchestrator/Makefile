SERVICE_NAME := $(notdir $(CURDIR))
DOCKER_IMAGE := $(SERVICE_NAME)-service
DOCKERFILE_PATH := ./Dockerfile
PORT ?= 8003

install: 
	pip install -r requirements.txt

lint:  
	flake8 src tests --count --statistics
	black --check src tests
	mypy src

format: 
	black src tests
	isort src tests

test: 
	pytest tests/ -v --cov=src --cov-report=term-missing

run: 
	uvicorn src.main:app --reload --host 0.0.0.0 --port $(PORT)

docker-build: 
	docker build \
		--build-arg SERVICE_NAME=$(SERVICE_NAME) \
		--build-arg PORT=$(PORT) \
		-t $(DOCKER_IMAGE):latest \
		-f $(DOCKERFILE_PATH) \
		./
	
docker-run:  
	docker run -d \
		--name $(SERVICE_NAME) \
		-p $(PORT):$(PORT) \
		--restart unless-stopped \
		$(DOCKER_IMAGE):latest

docker-stop: 
	docker stop $(SERVICE_NAME) || true
	docker rm $(SERVICE_NAME) || true

logs:  
	docker logs -f $(SERVICE_NAME)
