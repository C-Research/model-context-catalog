## ADDED Requirements

### Requirement: Dotpath resolution reuses mcc.pyrunner.resolve
All `pysrc` tools that identify a target object SHALL accept a dotpath string in either `module.attr` or `module:attr.attr` form, and SHALL resolve it by calling `resolve()` imported from `mcc.pyrunner`, unmodified. No `pysrc` tool SHALL re-implement dotpath parsing.

#### Scenario: Colon-separated path resolves a nested attribute
- **WHEN** a `pysrc` tool is called with `fn_path="mcc.db:ToolIndex.query"`
- **THEN** it resolves by importing `mcc.db` and traversing `ToolIndex` then `query`, via `mcc.pyrunner.resolve`

#### Scenario: Dot-separated path resolves a module-level attribute
- **WHEN** a `pysrc` tool is called with `fn_path="mcc.loader.load_file"`
- **THEN** it resolves by importing `mcc.loader` and retrieving `load_file`, via `mcc.pyrunner.resolve`

#### Scenario: Malformed dotpath raises ImportError
- **WHEN** a `pysrc` tool is called with a dotpath that has no resolvable module or attribute segment
- **THEN** the underlying `ImportError` from `mcc.pyrunner.resolve` propagates to the caller as the tool's error result

### Requirement: get_docstring returns the resolved object's docstring
`get_docstring(fn_path: str) -> str` SHALL resolve `fn_path` and return `inspect.getdoc()` of the resolved object, or an empty string if it has no docstring.

#### Scenario: Class with a docstring
- **WHEN** `get_docstring` is called with `fn_path="mcc.db:ToolIndex"`
- **THEN** it returns `ToolIndex`'s class docstring

#### Scenario: Object without a docstring
- **WHEN** `get_docstring` is called on an object that has no docstring
- **THEN** it returns an empty string, not `None` or an error

### Requirement: get_source returns the resolved object's source code
`get_source(fn_path: str) -> str` SHALL resolve `fn_path` and return `inspect.getsource()` of the resolved object.

#### Scenario: Function source is returned verbatim
- **WHEN** `get_source` is called with `fn_path="mcc.loader:load_file"`
- **THEN** it returns the exact source text of `load_file`, including its signature and body

#### Scenario: Source unavailable
- **WHEN** `get_source` is called on an object with no retrievable source (e.g. a builtin or C-extension type)
- **THEN** the underlying `OSError`/`TypeError` from `inspect.getsource` propagates to the caller as the tool's error result

### Requirement: get_signature returns parameter and return-type metadata
`get_signature(fn_path: str) -> dict` SHALL resolve `fn_path` to a function or method and return a dict containing, at minimum, a `params` list (each with `name`, `type`, `required`, `default`) and a `return_type`. `*args`/`**kwargs` parameters SHALL be excluded from `params`.

#### Scenario: Function with required and optional parameters
- **WHEN** `get_signature` is called on a function with one required parameter and one parameter with a default value
- **THEN** the returned `params` list marks the first as `required: true` and the second as `required: false` with its default value included

#### Scenario: Variadic parameters excluded
- **WHEN** `get_signature` is called on a function accepting `*args` or `**kwargs`
- **THEN** those parameters do not appear in the returned `params` list

### Requirement: list_members lists a module's own top-level definitions
`list_members(module_path: str, kind: str = "all") -> list[dict]` SHALL resolve `module_path` as a module and return a list of `{name, kind, doc}` entries for functions and classes defined in that module (i.e. `__module__` matches `module_path`), excluding names merely imported into it. `doc` SHALL be the first line of `inspect.getdoc()` (or an empty string if none). The `kind` parameter SHALL filter results to `"function"`, `"class"`, or `"all"` (default).

#### Scenario: Module listing excludes re-exported imports
- **WHEN** `list_members` is called with `module_path="mcc.db"`, and `mcc.db` imports `AsyncElasticsearch` at module scope without defining it
- **THEN** `AsyncElasticsearch` does not appear in the returned list

#### Scenario: kind filter restricts to classes
- **WHEN** `list_members` is called with `module_path="mcc.db"` and `kind="class"`
- **THEN** only class members are returned, no functions

### Requirement: get_class_hierarchy returns MRO and direct subclasses
`get_class_hierarchy(fn_path: str) -> dict` SHALL resolve `fn_path` to a class and return a dict with `bases` (the class's MRO, excluding the class itself, as qualified name strings) and `subclasses` (direct subclasses currently known to the process, via `__subclasses__()`, as qualified name strings).

#### Scenario: Subclass of a known base is listed
- **WHEN** `get_class_hierarchy` is called on a class that has one already-imported subclass
- **THEN** that subclass's qualified name appears in the `subclasses` list

#### Scenario: Subclasses not yet imported are not discoverable
- **WHEN** a class has a subclass defined in a module that has not been imported anywhere in the running process
- **THEN** that subclass does not appear in `subclasses` (this is an accepted limitation of runtime introspection, not a defect)

### Requirement: get_file_location returns source file and line range
`get_file_location(fn_path: str) -> dict` SHALL resolve `fn_path` and return a dict with `file` (absolute source file path) and `lineno`/`endlineno` (the object's line range), derived from `inspect.getsourcefile()` and `inspect.getsourcelines()`.

#### Scenario: Function location is returned
- **WHEN** `get_file_location` is called with `fn_path="mcc.loader:load_file"`
- **THEN** the returned `file` is the absolute path to `mcc/loader.py`, and `lineno`/`endlineno` bound `load_file`'s definition

### Requirement: pysrc tools are restricted to the admin.dev group
All six `pysrc` tools SHALL be declared with `groups: [admin, dev]` in `toolsets/contrib/pysrc.yaml`, producing tool keys of the form `admin.dev.<name>` (e.g. `admin.dev.get_docstring`). `toolsets/contrib/pysrc.yaml` SHALL be registered in `toolsets/contrib/settings.yaml`'s `tools:` list.

#### Scenario: Tool key reflects admin.dev grouping
- **WHEN** the `pysrc` toolset is loaded
- **THEN** `get_docstring` is registered under the key `admin.dev.get_docstring`

#### Scenario: pysrc tools load when contrib settings are enabled
- **WHEN** MCC is started with `MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml`
- **THEN** all six `pysrc` tools are present in the loaded tool catalog
