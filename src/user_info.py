#!/usr/bin/python3
"""

from user_info import username, password

"""
import sys
import os
import configparser

from svg_config import USER_CONFIG_PATH
# ---
config = configparser.ConfigParser()
# ---
username, password = "", ""
# ---
if os.path.exists(USER_CONFIG_PATH):
    config.read(USER_CONFIG_PATH)
    username = config['DEFAULT'].get('hiacc', "")
    password = config['DEFAULT'].get('hipass_upload', "")
