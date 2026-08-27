.PHONY: test-user test-matches test-player test-team test-club-matches test-api

test-user:
	@./scripts/smoke/bbs-user.sh

test-matches:
	@./scripts/smoke/bbs-matches.sh

test-player:
	@./scripts/smoke/bbs-player.sh

test-team:
	@./scripts/smoke/bbs-team.sh

test-club-matches:
	@./scripts/smoke/bbs-club-matches.sh

test-api: test-user test-matches test-player test-team test-club-matches
