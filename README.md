![](images/logo.png)

##

Easily create data visualization of static or streaming data


## Get Started

```python

pip install easycharts

```

## Create EasyCharts Server

```python
# charts.py
from fastapi import FastAPI
from easycharts.charts import ChartServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    server.charts = await ChartServer.create(
        server,
        "test"
    )

    await server.charts.create_dataset(
        "test",
        labels=['a', 'b', 'c', 'd'],
        dataset=[1,2,3,4]
    )
```
## Start Server

```bash
uvicorn --host 0.0.0.0 --port 0.0.0.0 charts:server

```

![](images/get-started-test.png)

## Update Data via API

In a separate window, access the OpenAPI docs to demonstrate dynanimc updates to the graph

```
http://0.0.0.0:8220/docs
```

![](images/get-started-update.png) 

## Line
![](images/get-started-test-1.png)


## Bar
![](images/get-started-test-1-bar.png)

## APIS

![](images/get-started-apis.png)

## Real World Usage - Resource Monitoring


```python
import asyncio
import datetime, psutil
from fastapi import FastAPI
from easycharts.charts import ChartServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    server.charts = await ChartServer.create(
        server,
        "test",
        chart_prefix = '/mycharts'
    )

    await server.charts.create_dataset(
        "test",
        labels=['a', 'b', 'c', 'd'],
        dataset=[1,2,3,4]
    )

    # set initial sync time
    label=datetime.datetime.now().isoformat()[11:19]
    await server.charts.create_dataset(
        'cpu',
        labels=[label],
        dataset=[psutil.cpu_percent()]
    )
    await server.charts.create_dataset(
        'mem',
        labels=[label],
        dataset=[psutil.virtual_memory().percent]
    )

    # create resource monitoring task 
    async def resource_monitor():
        while True:
            try:
                await asyncio.sleep(30)

                time_now=datetime.datetime.now().isoformat()[11:19]

                # updates CPU & MEM datasets with current time
                await server.charts.update_dataset(
                    'cpu',
                    label=time_now,
                    data=psutil.cpu_percent()
                )
                await server.charts.update_dataset(
                    'mem',
                    label=time_now,
                    data=psutil.virtual_memory().percent
                )
            except Exception:
                break
    asyncio.create_task(resource_monitor())
```

![](images/resource-mon.png)