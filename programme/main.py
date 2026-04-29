#!/usr/bin/python
# -*- coding:utf-8 -*-
import asyncio
import bluetoothManager

try:
    asyncio.run(bluetoothManager.main())
except KeyboardInterrupt:
    pass
