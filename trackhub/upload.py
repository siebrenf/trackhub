import tempfile
import os
import sys
import shlex
import subprocess as sp
import logging
from . import track
from . import genome
from . import base
from . import trackdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSYNC_OPTIONS = '--progress -rvL'


def run(cmds, **kwargs):
    """
    Wrapper around subprocess.run, with unicode decoding of output.

    Additional kwargs are passed to subprocess.run.
    """
    proc = sp.Popen(cmds, bufsize=-1, stdout=sp.PIPE, stderr=sp.STDOUT,
                    close_fds=sys.platform != 'win32')
    for line in proc.stdout:
        print(line[:-1].decode())
    retcode = proc.wait()
    if retcode:
        raise sp.CalledProcessError(retcode, cmd)


def symlink(target, linkname):
    """
    Create a symlink to `target` called `linkname`.

    Converts `target` and `linkname` to absolute paths; creates
    `dirname(linkname)` if needed.
    """
    target = os.path.abspath(target)
    linkname = os.path.abspath(linkname)
    if not os.path.exists(target):
        raise ValueError("target {} not found".format(target))

    link_dir = os.path.dirname(linkname)
    if not os.path.exists(link_dir):
        os.makedirs(link_dir)

    run(['ln', '-s', '-f', target, linkname])
    return linkname


def upload(host, user, local_dir, remote_dir, rsync_options=RSYNC_OPTIONS):
    """
    Upload a file or directory via rsync.

    Parameters
    ----------
    host : str or None
        If None, omit the host part and just transfer locally

    user : str or None
        If None, omit the user part

    local_dir : str
        If a directory, a trailing "/" will be added.

    remote_dir : str
        If a directory, a trailing "/" will be added.
    """
    if user is None:
        user = ""
    else:
        user = user + "@"
    if host is None or host == 'localhost':
        host = ""
    else:
        host = host + ":"

    if not local_dir.endswith('/'):
        local_dir = local_dir + '/'

    if not remote_dir.endswith('/'):
        remote_dir = remote_dir + '/'

    remote_string = '{user}{host}{remote_dir}'.format(**locals())
    cmds = ['rsync']
    cmds += shlex.split(rsync_options)
    cmds += [local_dir, remote_string]
    run(cmds)
    return [remote_string]


def local_link(local_fn, remote_fn, staging):
    """
    Creates a symlink to a local staging area.

    The link name is built from `remote_fn`, but the absolute path is put
    inside the staging directory.

    Example
    -------

    If we have the following initial setup::

        cwd="/home/user"
        local="data/sample1.bw"
        remote="/hubs/hg19/a.bw"
        staging="__staging__"

    Then this function does the equivalent of::

        mkdir -p __staging__/hubs/hg19
        ln -sf \\
            /home/user/data/sample1.bw \\
            /home/user/__staging__/hubs/hg19/a.bw
    """
    linkname = os.path.join(staging, remote_fn.lstrip(os.path.sep))
    return symlink(local_fn, linkname)


def stage(x, staging):
    """
    Stage an object to the `staging` directory.

    If the object is a Track and is one of the types that needs an index file
    (bam, vcfTabix), then the index file will be staged as well.

    Returns a list of the linknames created.
    """
    non_file_objects = (
        track.ViewTrack,
        track.CompositeTrack,
        genome.Genome,
    )

    if isinstance(x, non_file_objects):
        return []

    if not x.remote_fn:
        raise ValueError("Object does not have a valid `remote_fn` value")

    if not x.local_fn:
        raise ValueError("Object does not have a valid `local_fn` value")

    linknames = []

    def _stg(x, ext=''):
        linknames.append(
            local_link(x.local_fn + ext, x.remote_fn + ext, staging)
        )

    _stg(x)

    if isinstance(x, track.Track):
        if x.tracktype == 'bam':
            _stg(x, ext='.bai')
        if x.tracktype == 'vcfTabix':
            _stg(x, ext='.tbi')

    if isinstance(x, track.CompositeTrack):
        if x._html:
            _stg(x._html)

    return linknames


def stage_hub(hub, staging=None):
    """
    Stage a hub by symlinking all its connected files to a local directory.
    """
    linknames = []
    if staging is None:
        staging = tempfile.mkdtemp()
    for obj, level in hub.leaves(base.HubComponent, intermediate=True):
        linknames.extend(stage(obj, staging))
    return linknames


def upload_hub(host, user, hub, port=22, rsync_options=RSYNC_OPTIONS, staging=None):
    """
    Stages a hub and then uploads it.
    """
    if staging is None:
        staging = tempfile.mkdtemp()
    linknames = stage_hub(hub, staging=staging)
    hub_dir = os.path.dirname(hub.remote_fn)
    local_dir = os.path.join(staging, hub_dir.lstrip('/'))
    remote_dir = hub_dir
    upload(host, user, local_dir=local_dir, remote_dir=remote_dir, rsync_options=rsync_options)
    return linknames
