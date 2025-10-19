#!/usr/bin/python3
"""

from user_info import username, password

"""
import sys
import os
import configparser

from svg_config import user_config_path
# ---
config = configparser.ConfigParser()
# ---
username, password = "", ""
# ---
if os.path.exists(user_config_path):
    config.read(user_config_path)
    username = config['DEFAULT'].get('hiacc', "")
    password = config['DEFAULT'].get('hipass_upload', "")
else:
    print(f"Warning: Configuration file not found at {user_config_path}", file=sys.stderr)
