#!/usr/local/opt/python/bin/python3.7
"""Command line script for rendering Adblock Plus filter lists."""

import argparse
import io
import logging
import sys
import re
import requests
import json
import datetime

from os import path, remove, makedirs
from requests.exceptions import HTTPError
from abp.filters.sources import TopSource, WebSource, NotFound
from abp.filters.renderer import render_filterlist, IncludeError, MissingHeader

__all__ = ['main']

# Global variable to allocate config data.
configs = ''


def load_config():
    """Set config variable, loading data from 'filterlistsIndex' file."""
    global configs
    with open('filterlistsIndex.json') as json_file:
        data = json.load(json_file)

    # If no list name is specified it sets 'EasyList' as default.
    # if list_name == '-':
    #     list_name = 'EasyList'

    configs = data
    # for list in data:
    #     if list_name == list['name']:
    #         config = list

    # if config == '':
    #     sys.exit(
    #         'Error: {} does not exist on filterlistsIndex file.'.format(
    #             list_name))


def get_hg_commit(date, config):
    """Get commit number from a mercurial repository.

    To do:
    ------
    Implement function

    Parameters
    ----------
    date : date from required commit.

    Returns
    -------
    commit : returns commit number.
    """
    print('')


def get_git_commit(date, config):
    """Get commit number from a git repository.

    Parameters
    ----------
    date : date from required commit.

    Returns
    -------
    commit : returns commit number.
    """
    # date format = YYYY-MM-DDTHH:MM:SSZ
    url = 'https://api.github.com/repos/(owner)/(name)/commits'
    start_date = date + 'T00:00:00Z'
    end_date = date + 'T23:59:59Z'

    url = url.replace('(owner)', config['repository']['owner'])
    url = url.replace('(name)', config['repository']['name'])

    try:
        response = requests.get(
            url,
            params=[('until', start_date)])
        response.raise_for_status()
    except HTTPError as http_err:
        sys.exit(http_err)
    except Exception as err:
        sys.exit(err)
    else:
        response = json.loads(response.content)
        commit = response[0]['sha']
        return commit


def get_glab_commit(date, config):
    """Get commit number from a git repository.

    Parameters
    ----------
    date : date from required commit.

    Returns
    -------
    commit : returns commit number.
    """
    # date format = YYYY-MM-DDTHH:MM:SSZ
    # url = 'https://api.github.com/repos/(owner)/(name)/commits'
    url = 'https://gitlab.com/api/v4/projects/(projectId)/repository/commits'
    start_date = date + 'T00:00:00Z'
    end_date = date + 'T23:59:59Z'

    url = url.replace('(projectId)', config['repository']['projectId'])

    try:
        response = requests.get(
            url,
            params=[('until', start_date)])
        response.raise_for_status()
    except HTTPError as http_err:
        sys.exit(http_err)
    except Exception as err:
        sys.exit(err)
    else:
        response = json.loads(response.content)
        commit = response[0]['id']
        return commit


def parse_args():
    """Define all parameters script is going to accept."""
    date_help = 'Commit date in format "YYYY-MM-DD". Default is '\
                '"latest/master" commit'

    parser = argparse.ArgumentParser(description='Render a filter list.')
    parser.add_argument(
        'list', default='-', nargs='?',
        help='filter list to be render, name should exist on filterlistsIndex')
    parser.add_argument(
        '-d', '--date', action='store', default='-', nargs='?',
        help=date_help)
    parser.add_argument(
        '-c', '--commit', action='store', default='-', nargs='?',
        help='Commit number SHA number. Default is "latest/master/tip" branch')
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help='log included files and URLs')
    return parser.parse_args()


def create_file(commit, config):
    """Create temporal file for template needed.

    Parameters
    ----------
    commit: commit number. Temp file is going have it as name.

    Returns
    -------
    tmp_file : returns temp file name.
    """
    current_path = path.dirname(path.realpath(__file__))
    full_path = '{}{}{}'.format(current_path,
                                '/templates/', config['template'])
    tmp_file = '{}{}{}'.format('snapshots/', commit, '.tmp')
    tmp_path = '{}{}{}'.format(current_path, '/', tmp_file)

    try:
        # Make snapshots directory if doesn't exist.
        if not path.exists('snapshots'):
            makedirs('snapshots')

        filterListFolder = '{}{}'.format('snapshots/', config['template'].removesuffix(".txt"))
        if not path.exists(filterListFolder):
            makedirs(filterListFolder)

        with io.open(full_path, encoding='utf-8') as open_file:
            with io.open(tmp_path, 'w', encoding='utf-8') as out_fp:
                for line in open_file:
                    out_fp.write(line.replace('(branch)', commit))
    except (MissingHeader, NotFound, IncludeError) as exc:
        sys.exit(exc)

    return tmp_file


def main():
    """Call render function from python-abp."""
    commit = ''
    append = ''
    sources = {
        'http': WebSource('http'),
        'https': WebSource('https'),
    }
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                            format='%(message)s')

    
    # Load initial config.
    load_config()
    for config in configs:
      try:
        # Set initial variables depending on the repo type.
        if args.date == '-' and args.commit == '-':
            if config['repository']['type'] == 'git':
                commit = 'master'
            elif config['repository']['type'] == 'hg':
                commit = 'tip'
            else:
                commit = config['repository']['name']
            append = commit
        elif args.commit != '-':
            commit = args.commit
            append = commit
        else:
            # Validate date format.
            datetime.datetime.strptime(args.date, '%Y-%m-%d')
            if config['repository']['type'] == 'git':
                commit = get_git_commit(args.date, config)
            elif config['repository']['type'] == 'glab':
                commit = get_glab_commit(args.date, config)
            elif config['repository']['type'] == 'hg':
                # commit = get_hg_commit(args.date)
                print('Not generated file for: "{}"'.format(
                  config['name']))
                continue
                # sys.exit('Not implemented yet.')
            append = args.date

        tmp_file = create_file(commit, config)
        out_file = '{}{}{}{}{}{}{}'.format('snapshots/',
                                       config['template'].removesuffix(".txt"),
                                       '/',
                                       config['template'].removesuffix(".txt"),
                                       '-', append, '.txt')

      except ValueError as err:
        sys.exit(err)

      try:
        # Render list and put into a file.
        lines = render_filterlist(tmp_file, sources, TopSource())

        # Write rendered list into a file.
        with io.open(out_file, 'w', encoding='utf-8') as out_fp:
            for line in lines:
                if '! Title:' in line.to_string():
                    out_fp.write(
                        '{}{}{}{}'.format(
                            line.to_string(), ' ', append, '\n'))
                elif '! Last modified:' in line.to_string() or \
                    '! Expires:' in line.to_string():
                    pass
                else:
                    out_fp.write(line.to_string() + '\n')
      except (MissingHeader, NotFound, IncludeError) as exc:
        sys.exit(exc)

      # Removes temp file.
      if path.isfile(tmp_file):
        remove(tmp_file)
      else:
        sys.exit('Error: {} file not found'.format(tmp_file))

      print('Generated file: "{}" from date: "{}" and commit: "{}"'.format(
        out_file, args.date, commit))


if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
