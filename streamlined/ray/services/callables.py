from __future__ import annotations

import inspect
from typing import Any, Callable, ClassVar, Dict, Optional

import ray
import wrapt
from decorator import decorator


def check_enabled() -> bool:
    return RayRemote.ENABLED


class RayRemote:
    """
    Combining [`ray.remote`](https://docs.ray.io/en/master/package-ref.html#ray-remote) and invoke of remote function.

    Usage
    --------

    ```
    @RayRemote(...)
    def func(...):
        ...
    ```
    """

    ENABLED: ClassVar[bool] = True

    def __init__(
        self,
        wrapped: Optional[Callable] = None,
        *,
        num_returns: Optional[int] = None,
        num_cpus: Optional[float] = None,
        num_gpus: Optional[int] = None,
        resources: Optional[Dict[str, float]] = None,
        accelerator_type: Optional[Any] = None,
        max_calls: Optional[int] = None,
        max_restarts: Optional[int] = None,
        max_task_retries: Optional[int] = None,
        max_retries: Optional[int] = None,
        runtime_env: Optional[Dict[str, Any]] = None,
        retry_exceptions: Optional[bool] = None,
    ):
        """
        Args:
            num_returns (int): This is only for *remote functions*. It specifies
                the number of object refs returned by
                the remote function invocation.
            num_cpus (float): The quantity of CPU cores to reserve
                for this task or for the lifetime of the actor.
            num_gpus (int): The quantity of GPUs to reserve
                for this task or for the lifetime of the actor.
            resources (Dict[str, float]): The quantity of various custom resources
                to reserve for this task or for the lifetime of the actor.
                This is a dictionary mapping strings (resource names) to floats.
            accelerator_type: If specified, requires that the task or actor run
                on a node with the specified type of accelerator.
                See `ray.accelerators` for accelerator types.
            max_calls (int): Only for *remote functions*. This specifies the
                maximum number of times that a given worker can execute
                the given remote function before it must exit
                (this can be used to address memory leaks in third-party
                libraries or to reclaim resources that cannot easily be
                released, e.g., GPU memory that was acquired by TensorFlow).
                By default this is infinite.
            max_restarts (int): Only for *actors*. This specifies the maximum
                number of times that the actor should be restarted when it dies
                unexpectedly. The minimum valid value is 0 (default),
                which indicates that the actor doesn't need to be restarted.
                A value of -1 indicates that an actor should be restarted
                indefinitely.
            max_task_retries (int): Only for *actors*. How many times to
                retry an actor task if the task fails due to a system error,
                e.g., the actor has died. If set to -1, the system will
                retry the failed task until the task succeeds, or the actor
                has reached its max_restarts limit. If set to `n > 0`, the
                system will retry the failed task up to n times, after which the
                task will throw a `RayActorError` exception upon :obj:`ray.get`.
                Note that Python exceptions are not considered system errors
                and will not trigger retries.
            max_retries (int): Only for *remote functions*. This specifies
                the maximum number of times that the remote function
                should be rerun when the worker process executing it
                crashes unexpectedly. The minimum valid value is 0,
                the default is 4 (default), and a value of -1 indicates
                infinite retries.
            runtime_env (Dict[str, Any]): Specifies the runtime environment for
                this actor or task and its children. See
                :ref:`runtime-environments` for detailed documentation. This API is
                in beta and may change before becoming stable.
            retry_exceptions (bool): Only for *remote functions*. This specifies
                whether application-level errors should be retried
                up to max_retries times.
        """
        kwargs = {
            name: value
            for name, value in locals().items()
            if name != "self" and name != "kwargs" and name != "wrapped" and value is not None
        }

        self.__ray_wrapper = ray.remote(**kwargs) if kwargs else ray.remote

        if wrapped:
            raise ValueError(f"{self.__class__.__name__} should be initialized with arguments")

    def run_remote(self, fn: Callable, *args: Any, **kwargs: Any) -> ray.ObjectRef:
        """
        Run a callable in ray.

        This is short for `ray.remote(fn).remote(*args, **kwargs)`.
        """
        ray_callable = self.__ray_wrapper(fn)
        return ray_callable.remote(*args, **kwargs)

    @wrapt.decorator(enabled=check_enabled)
    def __call__(self, wrapped, instance, args, kwargs):
        if not callable(wrapped):
            raise TypeError(f"{self.__class__.__name__} should decorate a callable")

        if instance is None:
            if inspect.isclass(wrapped):
                raise TypeError(f"{self.__class__.__name__} cannot decorate a class")
            elif inspect.isfunction(wrapped):
                return self.run_remote(wrapped, *args, **kwargs)
            else:
                try:
                    # is callable
                    cls = getattr(wrapped, "__class__")
                    instance = wrapped
                    wrapped = cls.__call__
                except AttributeError:
                    return self.run_remote(wrapped, *args, **kwargs)

        @decorator
        def wrapper(fn: Callable, *args: Any, **kwargs: Any):
            return fn(*args, **kwargs)

        return self.run_remote(wrapper(wrapped), instance, *args, **kwargs)


def ray_remote(
    wrapped: Optional[Callable] = None,
    *,
    num_returns: Optional[int] = None,
    num_cpus: Optional[float] = None,
    num_gpus: Optional[int] = None,
    resources: Optional[Dict[str, float]] = None,
    accelerator_type: Optional[Any] = None,
    max_calls: Optional[int] = None,
    max_restarts: Optional[int] = None,
    max_task_retries: Optional[int] = None,
    max_retries: Optional[int] = None,
    runtime_env: Optional[Dict[str, Any]] = None,
    retry_exceptions: Optional[bool] = None,
):
    """
    Usage
    --------
    ```
    @ray_remote
    def func(...):
        ...
    ```

    ```
    @ray_remote(...)
    def func(...):
        ...
    ```

    See Also
    --------
    RayRemote
    """
    kwargs = {
        name: value
        for name, value in locals().items()
        if name != "kwargs" and name != "wrapped" and value is not None
    }

    if wrapped is None:
        return RayRemote(**kwargs)
    else:
        return RayRemote(**kwargs)(wrapped)
