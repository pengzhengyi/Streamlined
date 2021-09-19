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

```Python
LOG: {
    VALUE: ...,
    LEVEL: ...,
    LOGGER: ...
}
```

| Field Name | Field Value |
| --- | --- |
| **value** | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"Hello World!"</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda name: f"Welcome back {name}"</code></td></tr></tbody></table> |
| level | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>str</i></td><td><code>"debug"</code></td></tr><tr><td><i>int</i></td><td><code>logging.DEBUG</code></td></tr></tbody></table> |
| logger | <table><thead><tr><th>Type</th><th>Example</th></tr> </thead>  <tbody><tr><td><i>Logger</i></td><td><code>logging.getLogger()</code></td></tr><tr><td><a href="#Execution"><i>Execution</i></a></td><td><code>lambda logger_name: logging.getLogger(logger_name)</code></td></tr></tbody></table> |

### Pipeline

### Runstage


### Runstep

### Validator