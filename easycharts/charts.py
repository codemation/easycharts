import asyncio
import time, uuid, os
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from fastapi import Response
from fastapi.responses import HTMLResponse
from aiopyql.data import Database
from easyrpc.server import EasyRpcServer
from easyrpc.auth import encode

from easycharts.exceptions import (
    DuplicateDatasetError,
    MissingDatasetError
)
from easycharts.frontend import get_chart_body, get_chart_page

class ChartType(str, Enum):
    bar = 'bar'
    line = 'line'

class ChartServer:
    def __init__(self,
        rpc_server: EasyRpcServer,
        charts_db: Database = None
    ):
        self.rpc_server = rpc_server
        self.log = rpc_server.log
        self.db = charts_db

    @classmethod
    async def create(cls,
        server,
        charts_db: str,
        chart_prefix = '/chart'
    ):
        rpc_server = EasyRpcServer(
            server, 
            '/ws/charts',
            server_secret='easycharts' if not 'RPC_SECRET' in os.environ else os.environ['RPC_SECRET'],
        )

        charts_db = await Database.create(
            database=f"{charts_db}.db",
            cache_enabled=True
        )

        chart_server = cls(
            rpc_server,
            charts_db=charts_db
        )

        @server.get(chart_prefix + '/{chart}', response_class=HTMLResponse, tags=['charts'])
        async def view_chart_html(
            chart: str, 
            extra: str = None, 
            chart_type: ChartType = ChartType.line,
            body_only: bool = False
        ):
            charts = [chart]
            if extra:
                charts.append(extra)
            if not body_only:
                return await chart_server.get_chart_page(charts, chart_type=chart_type)
            return await chart_server.get_chart_body(charts, chart_type=chart_type)

        @server.post(chart_prefix + '/{chart}', tags=['charts'])
        async def update_chart(chart: str , label: str, data: str):
            return await chart_server.update_dataset(
                chart,
                label,
                data
            )
        @server.delete(chart_prefix + '/{chart}', tags=['charts'])
        async def delete_chart(chart: str):
            return await chart_server.remove_dataset(
                chart
            )
            
        class Dataset(BaseModel):
            name: str
            labels: list
            dataset: list

        @server.put(chart_prefix, tags=['charts'])
        async def create_chart(dataset: Dataset, response: Response):
            return await chart_server.create_dataset(
                dataset.name,
                dataset.labels,
                dataset.dataset,
                response=response
            )


        @server.on_event('shutdown')
        async def db_close():
            await charts_db.close()
            await asyncio.sleep(1)


        # create default rpc_server methods
        @rpc_server.origin(namespace='easycharts')
        async def create_chart(names: list, chart_type='line'):
            for name in names:
                if not name in chart_server.db.tables:
                    raise MissingDatasetError(name)
            datasets = []
            for name in names:
                dataset = await chart_server.db.tables[name].select('*')
                labels = [d['label'] for d in dataset]
                data = [d['data'] for d in dataset]
                datasets.append(
                    {
                        'name': name, 
                        'labels': labels,
                        'data': data,
                        "latest_timestamp": dataset[-1]['timestamp']
                    }
                )
            chart_id = '__and__'.join(names)
            return {
                "chart_id": f"{chart_id}_id",
                "name": chart_id,
                "names": names,
                "action": "create_chart",
                "type": chart_type,
                "datasets": datasets
            }

        @rpc_server.origin(namespace='easycharts')
        async def update_chart(name: str, latest_timestamp: float):
            if not name in chart_server.db.tables:
                raise MissingDatasetError(name)

            changes = await chart_server.db.tables[name].select(
                '*',
                where=[
                    ['timestamp', '>', latest_timestamp],
                ]
            )

            labels = [d['label'] for d in changes]
            data = [d['data'] for d in changes]
            if labels and data:
                return {
                    "name": name,
                    "action": "update_chart",
                    "latest_timestamp": changes[-1]['timestamp'],
                    "labels": labels,
                    "data": data
                }
            return {
                "info": f"{name} does not have any changes to update"
            }
        return chart_server


    async def create_dataset(self, 
        name: str,
        labels: list,
        dataset: list,
        response: Response = None
    ):
        if name in self.db.tables:
            self.log.warning(f"Dataset with name {name} already exists")
            if response:
                raise DuplicateDatasetError(name)
            return

        # create dataset table
        await self.db.create_table(
            name,
            [
                ('timestamp', float, 'UNIQUE NOT NULL'),
                ('label', str),
                ('data', str),
            ],
            'timestamp',
            cache_enabled=True
        )

        # load table with data
        for label, data in zip(labels, dataset):
            await self.db.tables[name].insert(
                timestamp=time.time(),
                label=label,
                data=data
            )
        return {'message': f"dataset {name} created"}

    async def update_dataset(self, 
        name: str,
        label: str, 
        data
    ):
        if not name in self.db.tables:
            raise MissingDatasetError(name)

        await self.db.tables[name].insert(
            timestamp=time.time(),
            label=label,
            data=data
        )
        return f"datapoint created"

    async def remove_dataset(self, 
        name
    ):
        if not name in self.db.tables:
            raise MissingDatasetError(name)

        await self.db.remove_table(name)
        return f"dataset {name} removed"
    def get_credentials(self):
        creds =  encode(
            'easycharts' if not 'RPC_SECRET' in os.environ else os.environ['RPC_SECRET'], 
            **{
                "type":"PROXY",
                "id": str(uuid.uuid1()),
                "namespace":"easycharts"
            }
        )
        return creds
    async def get_chart_page(self, name, chart_type='line'):
        return get_chart_page(name, self.get_credentials(), chart_type=chart_type)
    async def get_chart_body(self, name, chart_type='line'):
        return get_chart_body(name, self.get_credentials(), chart_type=chart_type)