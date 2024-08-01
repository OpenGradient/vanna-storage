run:
	docker-compose up

docker:
	docker build . -t vanna-storage

dev:
	python3 src/app.py
