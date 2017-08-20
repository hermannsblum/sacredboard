"""Module for managing TensorBoard processes."""
import re
from psutil import process_iter
from signal import SIGTERM

from sacredboard.app.process.process \
    import Process, ProcessError, UnexpectedOutputError

TENSORBOARD_BINARY = "tensorboard"


def stop_all_tensorboards():
    """Terminate all TensorBoard instances."""
    for process in Process.instances:
        print("Process '%s', running %d" % (process.command[0],
                                            process.is_running()))
        if process.is_running() and process.command[0] == "tensorboard":
            process.terminate()


class TensorboardNotFoundError(ProcessError):
    """TensorBoard binary not found."""
    pass


def run_tensorboard(logdir, listen_on="0.0.0.0", port=6006, tensorboard_args=None):
    """
    Launch a new TensorBoard instance.

    :param logdir: Path to a TensorFlow summary directory
    :param listen_on: The IP address TensorBoard should listen on.
    :param port: The Port TensorBoard should listen on
    :param tensorboard_args: Additional TensorBoard arguments.
    :return: Returns the port TensorBoard is listening on.
    :raise UnexpectedOutputError
    :raise TensorboardNotFoundError
    """
    if tensorboard_args is None:
        tensorboard_args = []

    # Kill running process on the port
    for proc in process_iter():
        try:
            for conns in proc.connections(kind='inet'):
                if conns.laddr[1] == port:
                    proc.send_signal(SIGTERM)  # or SIGKILL
                    continue
        except Exception:
            pass

    tensorboard_instance = Process.create_process(
        TENSORBOARD_BINARY.split(" ") +
        ["--logdir", logdir, "--host", listen_on, "--port", port] + tensorboard_args)
    try:
        tensorboard_instance.run()
    except FileNotFoundError as ex:
        raise TensorboardNotFoundError(ex)

    return port
