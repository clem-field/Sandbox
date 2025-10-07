
import  argparse, csv, datetime, hashlib, json, lxml, make_uuid, openpyxl, os, requests, sys, textwrap, time, uuid, yaml
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
from colorama import Fore, Back, Style
from datetime import datetime
from docx import Document
from jsonschema import validate
from pathlib import Path