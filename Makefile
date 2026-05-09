.PHONY: sync up

# Path to your private preferences repo (clone it alongside babyclaw)
PREFERENCES_DIR ?= ../babyclaw-preferences

sync:
	@test -d "$(PREFERENCES_DIR)" || { echo "ERROR: $(PREFERENCES_DIR) not found. Clone your private babyclaw-preferences repo there first."; exit 1; }
	cp "$(PREFERENCES_DIR)/vendir/vendir.yml" ./vendir.yml
	cp "$(PREFERENCES_DIR)/docker-compose.yml" ./docker-compose.yml
	vendir sync
	@echo "Config synced from $(PREFERENCES_DIR)"

up: sync
	docker-compose up -d
