import tempfile
import os
import shlex
import subprocess as sp
import logging
from . import track

logger = logging.getLogger(__name__)

RSYNC_OPTIONS = '--progress -rvL'


def run(cmds, env=None, **kwargs):
    try:
        p = sp.run(cmds, stdout=sp.PIPE, stderr=sp.STDOUT, check=True, env=env, **kwargs)
        p.stdout = p.stdout.decode(errors='replace')
    except sp.CalledProcessError as e:
        e.stdout = e.stdout.decode(errors='replace')
        logger.error('COMMAND FAILED: %s', ' '.join(e.cmd))
        logger.error('STDOUT+STDERR:\n%s', e.stdout)
        raise e
    return p


def symlink(target, linkname):
    target_dir = os.path.dirname(target)
    link_dir = os.path.dirname(linkname)
    link_base = os.path.basename(linkname)
    rel_target = os.path.relpath(target, link_dir)
    abs_target = os.path.abspath(target)
    if not os.path.exists(link_dir):
        os.makedirs(link_dir)
    run(['ln', '-s', '-f', abs_target, link_base], cwd=link_dir)
    return linkname


def upload_file(host, user, local_dir, remote_dir,
                rsync_options=RSYNC_OPTIONS):
    if user is None:
        user = ""
    else:
        user = user + "@"
    if host is None or host == 'localhost':
        host = ""
    else:
        host = host + ":"
    remote_string = '{user}{host}{remote_dir}'.format(**locals())
    cmds = ['rsync']
    cmds += shlex.split(rsync_options)
    cmds += [local_dir, remote_string]
    run(cmds)
    return [remote_string]


def local_link(local_fn, remote_fn, staging):
    """
    local: data/bigwig/sample1.bw
    remote: /hubs/hg19/a.bw

    cd __staging__/hubs/hg19
    ln -sf ../data/bigwig/sample1.bw a.bw
    """
    linkname = os.path.join(staging, remote_fn.lstrip(os.path.sep))
    symlink(os.path.abspath(local_fn), os.path.abspath(linkname))


def stage(x, staging, ext=''):
    local_link(x.local_fn + ext, x.remote_fn + ext, staging)


def upload_hub(host, user, hub, port=22, rsync_options=RSYNC_OPTIONS, staging=None):

    if staging is None:
        staging = tempfile.mkdtemp()

    stage(hub, staging)
    stage(hub.genomes_file, staging)
    for genome in hub.genomes_file.genomes:
        stage(genome.genome_file_obj, staging)
    for t, level in hub.leaves(track.CompositeTrack, intermediate=True):
        if t._html:
            stage(t._html, staging)

    for t, level in hub.leaves(track.Track):
        stage_track(t, staging)

    # do the final upload
    if not staging.endswith(os.path.sep):
        staging = staging + '/'

    upload_file(host, user, local_dir=staging, remote_dir='/', rsync_options=rsync_options)


def stage_track(track, staging):
    stage(track, staging)
    if track.tracktype == 'bam':
        stage(track, staging, ext='.bai')
    if track.tracktype == 'vcfTabix':
        stage(track, staging, ext='.tbi')
