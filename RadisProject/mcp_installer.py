# Timeout constants
DEFAULT_TIMEOUT = 300.0  # Default timeout in seconds
PACKAGE_TIMEOUTS = {
    "@modelcontextprotocol/server-browser": 480.0,
    "puppeteer": 600.0,
    # Add other package timeouts here
}


def _get_dynamic_timeout(self, package_name: str) -> float:
    # Check for exact match first
    if package_name in PACKAGE_TIMEOUTS:
        return PACKAGE_TIMEOUTS[package_name]

    # Check for partial matches
    for pattern, timeout in PACKAGE_TIMEOUTS.items():
        if pattern in package_name:
            return timeout

    # Return default timeout if no matches found
    return DEFAULT_TIMEOUT
