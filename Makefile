ADDONS_SOURCE_PATH = ../addons-source/NameSuite

.PHONY: update-pr sync-windows

update-pr:
	rm -rf $(ADDONS_SOURCE_PATH)/*
	./sync_to_gramps.sh
	./add_license.sh $(ADDONS_SOURCE_PATH)

sync-windows:
	./sync_to_windows.sh
