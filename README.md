# Streamlined

**Making running scripts more streamlined!**

Streamlined allows you to declare a pipeline using a declarative syntax.

## Install

Steamlined can be installed by running:

```bash
pip install streamlined
```

## QuickStart

Create a logger that log message less severe than INFO to stdout and others to stderr.

Instead, you can also use a customized logger as long as it has a [log method](https://docs.python.org/3/library/logging.html#logging.Logger.log).

```python
from streamlined.utils import create_logger, conditional_stream_mixin

logger = create_logger(name="pipeline", mixins=[conditional_stream_mixin])
```

Define the Pipeline configuration

```Python
import logging
from streamlined import Pipeline
from streamlined.constants import *

pipeline = Pipeline({
    NAME: "adding two numbers",
    ARGUMENTS: [
        {
            NAME: "x",
            VALUE: lambda: int(input('x = ')),
            LOG: {
                VALUE: lambda _value_: f"x is set to {_value_}",
                LEVEL: logging.INFO,
                LOGGER: logger
            }
        },
        {
            NAME: "y",
            VALUE: lambda: int(input('y = ')),
            LOG: {
                VALUE: lambda _value_: f"y is set to {_value_}",
                LEVEL: logging.INFO,
                LOGGER: logger
            }
        }
    ],
    RUNSTAGES: [
        {
            NAME: "compute sum",
            ACTION: lambda x, y: x + y,
            LOG: {
                VALUE: lambda _value_: f"x + y = {_value_}",
                LEVEL: logging.INFO,
                LOGGER: logger
            }
        }     
    ]
})
```

Run the Pipeline

```Python
pipeline.run()
```

## Components

### Notations

+ bolded **field name** implies a required field
+ bolded exposed magic value implies an argument value that is available to current scope and all enclosing scopes.

### Argument

Argument component is used to define a in-scope argument that can be utilized in execution component through dependency injection.

For example, suppose `x` is set to `1` and `y` is set to `x + 1` at arguments section of pipeline scope, then any execution component can access `x` and `y` by requiring them as function parameters.

```Python
pipeline = Pipeline({
    NAME: "adding two numbers",
    ARGUMENTS: [
        {
            NAME: "x",
            VALUE: 1
        },
        {
            NAME: "y",
            VALUE: lambda x: x + 1
        }
    ],
    RUNSTAGES: [
        {
            NAME: "compute sum",
            ACTION: lambda x, y: x + y
        }     
    ]
})
```

Argument definition precedence:

1. Arguments in larger scope are defined earlier than arguments in smaller scope. For example, an argument in runstep can reference an argument in runstage in its definition, but not the reverse.
1. Arguments appear earlier in list are defined earlier than arguments appear later in list. For example, if `x` and `y` are first and second item in argument list. `y` can reference `x`, but not the reverse.

Argument naming conventions:

- Argument name are encouraged to be unique to avoid arguemnt shadowing. When multiple arguments share the same name, the the argument value in the nearest scope will be used. For example, if `x` is defined in pipeline to be `1` and in runstage `foo` to be `-1`, referencing `x` in a runstep inside `foo` will resolve to `-1` while in runstage `bar` will resolve to `1`.
- Argument name should follow [Python variable naming convention](https://www.python.org/dev/peps/pep-0008/#function-and-variable-names) when it needs to be referenced in execution components. *Explicit retrieval is possible if a variable is named differently like `"Menu Items"`, but it will not be as straightforward as dependency injection.*
- If an argument is only executed for the effect, its name is encouraged to be `"_"`.

#### Syntax

```
ARGUMENTS: [
    {
        name: ...,
        value: ...,
        logging: ...,
        cleanup: ...,
        validator: ...
    },
    ...
]
```

| Field Name | Field Value | Expose Magic Value |
| --- | --- | --- |
| **name** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"x"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda: "x"</code></td></tr></tbody></table>| `_name_` |
| **value** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Any</i></td><td><code>1</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda: random.randint(0, 100)</code></td></tr></tbody></table>| `_value_` |
| logging | See [Logging Component](#Logging)|
| cleanup | See [Cleanup Component](#Cleanup)|
| validator | See [Validator Component](#Validator)|

### Cleanup

Cleanup component is exactly the same as the execution component except it will be executed last. Therefore, it is perfect to perform some cleanup actions like closing a file, ending a database connection...

#### Syntax

```Python
CLEANUP: <action>
```

| Field Name | Field Value |
| --- | --- |
| **action** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Callable</i></td><td><code>lambda csvfile: csvfile.close()</code></td></tr></tbody></table> |

### Execution

Execution component is pivotal in pipeline definition as it can produce a new value utilizing already-defined values. 

The value for executed action can be any Callable -- a lambda or a function. And if this callable has any parameters, those values will be resolved at invocation time.

Dependency Injection will succeed if and only if parameter name match the name of a in-scope declared argument.

Possible ways of Argument Declaration:

- Through argument component (most frequent)
- Through automatically exposed magic values.
- Through explicitly bound argument -- calls of `bindone`, `bind`, `run`.

An argument is in scope if and only if it is defined in current scope or any enclosing scope. For example, if `x` is referenced in a runstep execution component, applicable scopes include this runstep scope, enclosing runstage scope, enclosing pipeline scope (global scope).

#### Syntax

```Python
ACTION: <action>
```

| Field Name | Field Value |
| --- | --- |
| **action** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Callable</i></td><td><code>lambda x, y: x + y</code></td></tr></tbody></table> |

### Logging

Logging component is responsible for logging running details of enclosing component.

If logger is not specified, it will use [`logging.getLogger()`](https://docs.python.org/3/library/logging.html#logging.getLogger) to retrieve a default logger. But it is more encouraged to pass in a customized logger befitting your need. The passed in logger should possess a `log(level, msg)` method.

`steamlined.utils.log` also expose some utilities methods to quickly create loggers. `create_logger` takes in a `name`, `level`, and `mixins` to create a logger. If `mixins` are not passed, then [current logger class](https://docs.python.org/3/library/logging.html#logging.getLoggerClass) is used to create a logger with specified `name` and `level`. `create_async_logger` takes same arguments and creates a multithreading-compatible equivalent.

#### Syntax

+ Full Syntax
    
    ```Python
    LOG: {
        VALUE: ...,
        LEVEL: ...,
        LOGGER: ...
    }
    ```

+ Only specify log message

    ```Python
    LOG: ...
    ```

| Field Name | Field Value |
| --- | --- |
| **value** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"Hello World!"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda name: f"Welcome back {name}"</code></td></tr></tbody></table> |
| level | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"debug"</code></td></tr><tr><td><i>int</i></td><td><code>logging.DEBUG</code></td></tr></tbody></table> |
| logger | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Logger</i></td><td><code>logging.getLogger()</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda logger_name: logging.getLogger(logger_name)</code></td></tr></tbody></table> |

### Pipeline

A pipeline component is the topmost-level of configuration. For example, arguments defined at this scope can be referenced in all other scopes. Pipeline is composed by a list of runstages and the return value of the pipeline component is the return values of runstages.

Also `_pipeline_` will be exposed as a magic property to reference current pipeline. To explicitly bind an argument at global level, `bindone(name, value)` can be used.

#### Skip

Skip is a special field present in pipeline configuration (it is also present in runstage component and runstep component) which controls conditionally execution of enclosing component.  

It can be configured in any of the following ways:

- Boolean Flag: `"skip": True` or `"skip": False`
- An execution component that evaluates to boolean flag
    `"skip": lambda: True`
- A dictionary where value determines whether enclosing component should be skipped and action specifies an action to execute in replacement if enclosing component is skipped.

    ```Python
    "skip": {
        "value": True,
        "action": lambda: print('skipped')
    }
    ```

- Not specifying any, it will default to `"skip": False`

#### Syntax

```Python
{
    NAME: ...,
    TAG: ...,
    ARGUMENTS: ...,
    RUNSTAGES: ...,
    CLEANUP: ...,
    VALIDATOR: ...,
    SKIP: ...
}
```

| Field Name | Field Value | Expose Magic Value |
| --- | --- | --- |
| **name** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"x"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda: "x"</code></td></tr></tbody></table>| `_name_` |
| tags | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>List[str]</i></td><td><code>["preparation", "important"]</code></td></tr></tbody></table>| `_tags_` |
| arguments | See [Argument Component](#Argument)|
| runstages | See [Runstage Component](#Runstage)|
| validator | See [Validator Component](#Validator)|
| skip | See [Skip field](#Skip)|

### Runstage

Runstage is the intermediate level between pipeline and runstep -- pipeline is composed of a list of runstages while a runstage is composed of a list of runsteps. In other words, runstage represent a grouping of runsteps.

Arguments defined in runstage will be available through dependency injection to all enclosed runsteps.

Runstage exposes a magic property `_runsteps_` which represent enclosed runsteps. It can be used to explicitly bind an argument at runsteps level. For example, if first runstage exposes an argument through `lambda _runsteps_: _runsteps_.bindone('x', 1)` can be used, later runstages can reference `x` through dependency injection.

Runstage also has a special `action` field. When this field is not specified, the default action is to run in order the enclosed runsteps (equivalent of calling `_runsteps_.run()`) and collect all return values as a list. If `action` is specified, then this action is responsible for running runsteps explicitly if necessary.

#### Syntax

```Python
RUNSTAGES: [
    {
        NAME: ...,
        TAG: ...,
        ARGUMENTS: ...,
        RUNSTEPS: ...,
        ACTION: ...,
        LOG: ...,
        CLEANUP: ...,
        VALIDATOR: ...,
        SKIP: ...
    },
    ...
]
```

| Field Name | Field Value | Expose Magic Value |
| --- | --- | --- |
| **name** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"x"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda: "x"</code></td></tr></tbody></table>| `_name_` |
| tags | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>List[str]</i></td><td><code>["preparation", "important"]</code></td></tr></tbody></table>| `_tags_` |
| arguments | See [Argument Component](#Argument)|
| runsteps | See [Runstep Component](#Runstep)| **`_runsteps_`** |
| **action** | See [Execution Component](#Execution)|
| log | See [Log Component](#Log)|
| cleanup | See [Cleanup Component](#Cleanup)|
| validator | See [Validator Component](#Validator)|
| skip | See [Skip field](#Skip)|

### Runstep

Runstep is the lowest running unit of pipeline. It should ideally represent a trivial task like running a shell script. This task should be defined as the `action` field.

#### Syntax

```Python
RUNSTAGES: [
    {
        NAME: ...,
        TAG: ...,
        ARGUMENTS: ...,
        ACTION: ...,
        LOG: ...,
        CLEANUP: ...,
        VALIDATOR: ...,
        SKIP: ...
    },
    ...
]
```

| Field Name | Field Value | Expose Magic Value |
| --- | --- | --- |
| **name** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"x"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda: "x"</code></td></tr></tbody></table>| `_name_` |
| tags | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>List[str]</i></td><td><code>["preparation", "important"]</code></td></tr></tbody></table>| `_tags_` |
| arguments | See [Argument Component](#Argument)|
| action | See [Execution Component](#Execution)|
| log | See [Log Component](#Log)|
| cleanup | See [Cleanup Component](#Cleanup)|
| validator | See [Validator Component](#Validator)|
| skip | See [Skip field](#Skip)|

### Validator

Validator component enables validation before or after execution of enclosing component's action. If validation failed, the execution of pipeline will immediately fail because of thrown validation exception.

A common use case is to validate a file not exists before action execution and exists after execution when the enclosing component's action involves creating a new file.

A validator component is composed by before validation stage and (or) after validation stage. Each validation stage is then composed by a predicate that evaluates to a boolean and a log field which is a dictionary from True or False to a logging component configuration.

#### Syntax

+ Full Syntax

    ```Python
    VALIDATOR: {
        VALIDATION_BEFORE_STAGE: {
            ACTION: ...,
            LOG: {
                True: ...,
                False: ...
            },
        },
        VALIDATION_AFTER_STAGE: {
            ACTION: ...,
            LOG: {
                True: ...,
                False: ...
            },
        },
    }
    ```

+ Specify only before validation stage

    ```Python
    VALIDATOR: {
        VALIDATION_BEFORE_STAGE: {
            ACTION: ...,
            LOG: {
                True: ...,
                False: ...
            },
        }
    }
    ```

+ Specify only after validation stage

    ```Python
    VALIDATOR: {
        VALIDATION_AFTER_STAGE: {
            ACTION: ...,
            LOG: {
                True: ...,
                False: ...
            },
        }
    }
    ```

    This can be further simplified to

    ```Python
    VALIDATOR: {
        ACTION: ...,
        LOG: {
            True: ...,
            False: ...
        }
    }
    ```

| Field Name | Field Value |
| --- | --- | 
| before | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Callable[..., bool]</i></td><td><code>lambda: True</code></td></tr><tr><td>Dict</a></td><td><code>{"action": lambda: True, LOG: {True: "pass", False: "fail"}}</code></td></tr></tbody></table>|
| after | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Callable[..., bool]</i></td><td><code>lambda: True</code></td></tr><tr><td>Dict</a></td><td><code>{"action": lambda: True, LOG: {True: "pass", False: "fail"}}</code></td></tr></tbody></table>|

There are several variants to validation stage configuration:

+ Full syntax

    ```Python
    {
        ACTION: ...,
        LOG: {
            True: ...,
            False: ...
        }
    }
    ```

+ Use default log message


    ```Python
    {
        ACTION: ...
    }
    ```

| Field Name | Field Value |
| --- | --- |
| **True** | See [Argument Component](#Logging) |
| **False** | See [Argument Component](#Logging) |

## Utilities

This section will cover some utilities exposed by `streamlined` library. All these utilities are put under `streamlined.utils` package.

### Argument Parser/Loader

+ `streamlined.utils.ArgumentParser` is a utility built on top of [argparse](https://docs.python.org/3/library/argparse.html) to parse command line arguments iteratively. See `utils/argument_parser.py` folder for more details.
+ `streamlined.utils.ArgumentLoader` allows specifying definition for argument parser inside the [dataclass](https://docs.python.org/3/library/dataclasses.html) definition -- through the `metadata` property of dataclass field. 

    It supports
    
    + creating an argument parser based on defined dataclass fields
    + creating an instance from arguments using a provided argument parser
    + create an instance from arguments directly (the argument parser is created based off configuration in defined dataclass fields)

    ```Python
    @dataclass
    class DatabaseConfig(ArgumentLoader):
        username: str = field(
            metadata={"name": ["-u", "--username"], "help": "supply username", "default": "admin"}
        )
        password: str = field(
            metadata={"name": ["-p"], "help": "supply password", "dest": "password"}
        )
        database: InitVar[str] = field(
            metadata={"help": "supply value for database", "choices": ["mysql", "sqlite", "mongodb"]}
        )

        def __post_init__(self, database):
            pass
    ```

    After invoking `DatabaseConfig.from_arguments(<args>)`, an instance of
    DatabaseConfig will be created with all values loaded based on parsed arguments.

### Configuration Parser/Loader

+ `streamlined.utils.ConfigurationParser` is a derived class of [configparser.ConfigParser](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser) that provides the additional functionalities:

    + **CLASSMETHOD** add a section -- `append_section`
    + **CLASSMETHOD** remove a section -- `remove_section`
    + get an configuration option and cast to specified type -- `get_with_type`
+ `streamlined.utils.ConfigurationLoader` allows loading a configuration file into a [dataclass](https://docs.python.org/3/library/dataclasses.html).
It can be seen as a trait to be derived by desired dataclass:

    ```Python
    from dataclasses import dataclass
    from streamlined.utils import ConfigurationLoader


    @dataclass
    class FooConfig(ConfigurationLoader):
        bar: str
    ```

    After extending `ConfigurationLoader`,`FooConfig` can invoke `from_config_file(<config_filepath>, <section>)` to create an instance of
    FooConfig with all values loaded according to their annotation types.

    *ConfigurationLoader is able to handle `ClassVar` and `InitVar` as expected.*

### Concurrency

<!-- TODO: add description for concurrency-->