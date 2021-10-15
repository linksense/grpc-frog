#!/usr/bin/env python
# encoding: utf-8
# Copyright 2021 LinkSense Technology CO,. Ltd

# noinspection PyUnresolvedReferences
import datetime

# noinspection PyUnresolvedReferences
from typing import Dict, List

from pydantic import BaseModel as _BaseModel

# noinspection PyUnresolvedReferences
from grpc_frog import frog


class BaseModel(_BaseModel):
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
