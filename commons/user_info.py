#!/usr/bin/python3
"""

from user_info import username, password

"""
import os
import configparser

home_dir = os.getenv("HOME")
project = home_dir if home_dir else 'I:/core/bots/core1'
# ---
config = configparser.ConfigParser()
config.read(f"{project}/confs/user.ini")

username = config['DEFAULT'].get('hiacc', "")
password = config['DEFAULT'].get('hipass_upload', "")
