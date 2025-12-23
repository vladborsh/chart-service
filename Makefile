# Podman configuration for Chart Service
# Podman is a daemonless container engine - a drop-in replacement for Docker

# Build the container image
build:
	podman build -t chart-service:latest .

# Run the container
run:
	podman run -d \
		--name chart-service \
		-p 8000:8000 \
		-e PYTHONUNBUFFERED=1 \
		-e LOG_LEVEL=INFO \
		--restart unless-stopped \
		chart-service:latest

# Run with podman-compose (requires podman-compose installed)
compose-up:
	podman-compose up -d

compose-down:
	podman-compose down

# Stop and remove container
stop:
	podman stop chart-service
	podman rm chart-service

# View logs
logs:
	podman logs -f chart-service

# Check health
health:
	curl http://localhost:8000/health

# Shell into running container
shell:
	podman exec -it chart-service /bin/bash

# Clean up
clean:
	podman stop chart-service || true
	podman rm chart-service || true
	podman rmi chart-service:latest || true

.PHONY: build run compose-up compose-down stop logs health shell clean
