.PHONY: test-user test-matches test-api

test-user:
	@./scripts/smoke/bbs-user.sh

test-matches:
	@./scripts/smoke/bbs-matches.sh

test-api: test-user test-matches
