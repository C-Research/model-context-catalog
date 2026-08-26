## ADDED Requirements

### Requirement: Prometheus metrics endpoint
The server SHALL expose an anonymous `GET /metrics` HTTP route (`@route(anonymous=True)`) that returns Prometheus text-exposition-format output via `prometheus_client.generate_latest()`, reflecting the counters and histograms recorded per the `mcp-middleware` capability's metrics-recording requirement.

#### Scenario: Metrics reachable without credentials
- **WHEN** a `GET /metrics` request arrives with no API key
- **THEN** the server responds `200` with Prometheus-format metrics, not `401`

#### Scenario: Metrics reflect tool calls from both transports
- **WHEN** tool calls have been made via the MCP `execute` tool and via `POST /tools/{key}`
- **THEN** `GET /metrics` output includes both calls' contributions to `mcc_tool_calls_total` and `mcc_tool_call_duration_seconds`
