## ADDED Requirements

### Requirement: Admin contrib tool exposes cache statistics
A contrib tool `admin.cache_stats` SHALL be available when `contrib: true` is set. It SHALL call `cache.get_stats()` from cashews and return the result. The tool SHALL require no parameters and be restricted to the `admin` group.

#### Scenario: Cache stats returned
- **WHEN** an admin user calls `execute("admin.cache_stats")`
- **THEN** the current cashews cache statistics are returned

#### Scenario: Non-admin denied
- **WHEN** a non-admin user calls `execute("admin.cache_stats")`
- **THEN** the handler returns "Unauthorized"

#### Scenario: Available when contrib enabled
- **WHEN** `settings.contrib` is `true`
- **THEN** `admin.cache_stats` appears in search results for admin users
