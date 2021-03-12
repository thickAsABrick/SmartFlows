from ...error import LauncherError
from ...utils import get_logger
from ...utils.helpers import init_default
from .slurmCommands import salloc, scancel, sinfo
from .slurmLauncher import SlurmLauncher
from .slurmParser import parse_salloc, parse_salloc_error
from ..util.launcherUtil import ComputeNode, Partition

logger = get_logger(__name__)


def get_slurm_allocation(nodes=1, add_opts=None):
    """Request an allocation

    This function requests an allocation with the specified arguments.
    Anything passed to the add_opts will be processed as a Slurm
    argument and appended to the salloc command with the appropriate
    prefix (e.g. "-" or "--").

    The add_opts can be used to pass extra settings to the
    workload manager such as the following for Slurm:
        - nodelist="nid00004"

    For arguments without a value, pass None or and empty
    string as the value. For Slurm:
        - exclusive=None

    :param nodes: number of nodes for the allocation, defaults to 1
    :type nodes: int, optional
    :param add_opts: additional options for the slurm wlm
    :type add_opts: dict
    :raises LauncherError: if the allocation is not successful
    :return: the id of the allocation
    :rtype: str
    """
    add_opts = init_default({}, add_opts, dict)
    SlurmLauncher.check_for_slurm()

    salloc_args = _get_alloc_cmd(nodes, add_opts=add_opts)
    debug_msg = " ".join(salloc_args[1:])
    logger.debug(f"Allocation settings: {debug_msg}")

    _, err = salloc(salloc_args)
    alloc_id = parse_salloc(err)
    if alloc_id:
        logger.info(f"Allocation successful with Job ID: {str(alloc_id)}")
    else:
        logger.debug(err)
        error = parse_salloc_error(err)
        if not error:
            logger.error(err)
            raise LauncherError("Slurm allocation error")
        raise LauncherError(error)
    return str(alloc_id)


def release_slurm_allocation(alloc_id):
    """Free an allocations resources

    :param alloc_id: allocation id
    :type alloc_id: str
    :raises LauncherError: if allocation could not be freed
    """
    SlurmLauncher.check_for_slurm()

    logger.info(f"Releasing allocation: {alloc_id}")
    returncode, _, _ = scancel([str(alloc_id)])

    if returncode != 0:
        logger.error(f"Unable to revoke your allocation for jobid {str(alloc_id)}")
        logger.error(
            "The job may have already timed out, or you may need to cancel the job manually"
        )
        raise LauncherError(f"Unable to revoke your allocation for jobid  {str(alloc_id)}")

    logger.info(f"Successfully freed allocation {alloc_id}")


def validate(nodes=1, ppn=1, partition=None):
    """Check that there are sufficient resources in the provided Slurm partitions.

    if no partition is provided, the default partition is found and used.

    :param str partition: partition to validate
    :param nodes: Override the default node count to validate
    :type nodes: int
    :param ppn: Override the default processes per node to validate
    :type ppn: int
    :raises: LauncherError
    :returns: True if resources are available
    :rtype: bool
    """
    sys_partitions = _get_system_partition_info()

    n_avail_nodes = 0
    avail_nodes = set()

    p_name = partition
    if p_name is None or p_name == "default":
        try:
            p_name = get_default_partition()
        except LauncherError as e:
            raise LauncherError(
        "No partition provided and default partition could not be found") from e

    if not p_name in sys_partitions:
        raise LauncherError(f"Partition {p_name} is not found on this system")

    for node in sys_partitions[p_name].nodes:
        if node.ppn >= ppn:
            avail_nodes.add(node)

    n_avail_nodes = len(avail_nodes)
    logger.debug(f"Found {n_avail_nodes} nodes that match the constraints provided")

    if n_avail_nodes < nodes:
        logger.warning(
            f"{nodes} nodes are not available on the specified partitions.  Only "
            f"{n_avail_nodes} nodes available."
        )
        return False

    logger.info("Successfully validated Slurm with sufficient resources")
    return True


def get_default_partition():
    """Returns the default partition from Slurm

    This default partition is assumed to be the partition with
    a star following its partition name in sinfo output

    :returns: the name of the default partition
    :rtype: str
    """
    sinfo_output, _ = sinfo(["--noheader", "--format", "%P"])

    default = None
    for line in sinfo_output.split("\n"):
        if line.endswith("*"):
            default = line.strip("*")

    if not default:
        raise LauncherError("Could not find default partition!")
    return default


def _get_system_partition_info():
    """Build a dictionary of slurm partitions
    :returns: dict of Partition objects
    :rtype: dict
    """

    sinfo_output, _ = sinfo(["--noheader", "--format", "%R %n %c"])

    partitions = {}
    for line in sinfo_output.split("\n"):
        line = line.strip()
        if line == "":
            continue

        p_info = line.split(" ")
        p_name = p_info[0]
        p_node = p_info[1]
        p_ppn = int(p_info[2])

        if not p_name in partitions:
            partitions.update({p_name: Partition()})

        partitions[p_name].name = p_name
        partitions[p_name].nodes.add(ComputeNode(node_name=p_node, node_ppn=p_ppn))

    return partitions


def _get_alloc_cmd(nodes, add_opts=None):
    """Return the command to request an allocation from Slurm with
    the class variables as the slurm options."""

    salloc_args = [
        "--no-shell",
        "-N",
        str(nodes),
        "-J",
        "SmartSim",
    ]

    for opt, val in add_opts.items():
        short_arg = bool(len(str(opt)) == 1)
        prefix = "-" if short_arg else "--"
        if not val:
            salloc_args += [prefix + opt]
        else:
            if short_arg:
                salloc_args += [prefix + opt, str(val)]
            else:
                salloc_args += ["=".join((prefix + opt, str(val)))]

    return salloc_args
