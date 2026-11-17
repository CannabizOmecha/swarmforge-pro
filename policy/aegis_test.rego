package aegis.authorization_test

import data.aegis.authorization

test_allows_valid_local_synthetic_request if {
	authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 20,
		"network_enabled": false,
	}
}

test_denies_unknown_scope if {
	not authorization.allow with input as {
		"scope_id": "production",
		"operation": "execute",
		"batch_size": 20,
		"network_enabled": false,
	}
}

test_denies_unauthorized_operation if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "deploy",
		"batch_size": 20,
		"network_enabled": false,
	}
}

test_denies_zero_batch if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 0,
		"network_enabled": false,
	}
}

test_denies_oversized_batch if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 201,
		"network_enabled": false,
	}
}

test_denies_network_enabled_scope if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 20,
		"network_enabled": true,
	}
}

test_denies_extra_target_field if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 20,
		"network_enabled": false,
		"target_url": "https://example.invalid",
	}
}

test_denies_missing_network_flag if {
	not authorization.allow with input as {
		"scope_id": "local-synthetic",
		"operation": "execute",
		"batch_size": 20,
	}
}
