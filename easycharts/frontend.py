def get_chart_body(names: list, creds: str, chart_type: str):
    names_joined = '__and__'.join(names)
    names = [f'"{name}"' for name in names ]
    names_csv = ', '.join(names)
    return f"""
<canvas id="{names_joined}_id" width="1224" height="768"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function uuidv4() {{
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            }});
        }}
        var socket = new WebSocket("ws://" + window.location.host + "/ws/charts")
        socket.onopen = function(event) {{
            socket.send('{{"setup": "{creds}"}}');
            let names = [{names_csv}];
            onLoadCreateChart(names);
        }};

        //line chart config

        var createChart = function(chartId, type, name, labels, newDataSets){{
            console.log(labels);
            console.log(newDataSets);
            var getChartData = function(name, labels, newDataSets){{
                var dataSet = {{
                    labels: labels,
                    datasets: newDataSets
                }};
                return dataSet
            }};
            var ctx = document.getElementById(chartId);
            var newChart = new Chart(ctx, {{
                type: type,
                data: getChartData(name, labels, newDataSets),
                options: {{
                    responsive: true,
                    plugins: {{
                    legend: {{
                        position: 'top',
                    }},
                    title: {{
                        display: true,
                        text: name
                    }}
                }},
                }}
            }});
            return newChart
        }};

        var dataCharts = {{}}

        socket.onmessage = function(event) {{
            var parseCommand = JSON.parse(event.data)
            console.log(parseCommand)
            if ('ws_action' in parseCommand){{
                if (parseCommand['ws_action']['response']['action'] == 'create_chart'){{
                    chartName = parseCommand['ws_action']['response']['name']
                    dataCharts[chartName] = {{}}
                    var newDataSets = []
                    dataSetsLen = parseCommand['ws_action']['response']['datasets'].length
                    for (let index = 0; index < dataSetsLen; index++) {{
                        let ds = parseCommand['ws_action']['response']['datasets'][index];
                        dataCharts[ds.name] = {{}};
                        newDataSets.push(
                            {{
                                label: ds.name,
                                data: ds.data,
                                borderColor: "#" + Math.floor(Math.random()*16777215).toString(16),
                                backgroundColor: "#" + Math.floor(Math.random()*16777215).toString(16),
                            }}
                        );
                        dataCharts[ds.name]['index'] = index;
                        dataCharts[ds.name]['chartName'] = chartName;
                        dataCharts[ds.name]['latestTimestamp'] = ds.latest_timestamp;

                    }};
                    let labels = parseCommand['ws_action']['response']['datasets'][0].labels;
                    dataCharts[chartName + '_chart'] = createChart(
                        parseCommand['ws_action']['response']['chart_id'],
                        parseCommand['ws_action']['response']['type'],
                        parseCommand['ws_action']['response']['name'],
                        labels, // labels
                        newDataSets // data
                    );
                    //dataCharts[chartName]['latest_timestamp'] = parseCommand['ws_action']['response']['latest_timestamp']
                }}else if ( parseCommand.ws_action.response.action == 'update_chart' ){{
                    console.log("update_chart - results: " + parseCommand)
                    let datasetName = parseCommand['ws_action']['response']['name']
                    let chartIndex = dataCharts[datasetName].index
                    let chartName = dataCharts[datasetName].chartName

                    var chartToUpdate = dataCharts[chartName + '_chart'];
                    var changeLen = parseCommand['ws_action']['response']['data'].length
                    for (let index = 0; index < changeLen; index++) {{
                        chartToUpdate.data.datasets[chartIndex].data.push(
                            parseCommand['ws_action']['response']['data'][index]
                        );
                        let newLabel = parseCommand['ws_action']['response']['labels'][index]
                        if (!(chartToUpdate.data.labels.includes(newLabel))){{
                            chartToUpdate.data.labels.push(
                                newLabel
                            );
                        }}

                    }};
                    chartToUpdate.update();
                    dataCharts[datasetName]['latest_timestamp'] = parseCommand['ws_action']['response']['latest_timestamp'];
                }};
            }};
        }}
        var makeChart = function(names){{
            console.log(names);
            let namesJson = JSON.stringify({{'names': names, 'chart_type': '{chart_type}'}});
            let requestId = uuidv4();
            var getData = '{{"ws_action": {{"type": "request", "response_expected": true, "request": {{"action": "create_chart", "args": [], "kwargs": ' + namesJson + ' }}, "request_id": "' + requestId + '"}}}}';
            socket.send(getData)
        }};

        var updateChart = function(name){{
            let latestTimestamp = dataCharts[name].latestTimestamp;
            let requestId = uuidv4();
            var getData = '{{"ws_action": {{"type": "request", "response_expected": true, "request": {{"action": "update_chart", "args": ["'+ name + '",' +  latestTimestamp + '], "kwargs": {{}}}}, "request_id": "' + requestId + '"}}}}';
            socket.send(getData)
        }};

        var onLoadCreateChart = function(names) {{

            makeChart(names);
            console.log("onLoadCreateChart "+ names)
            var setUpdateInterval = function(name){{
                var updateChartName = function(){{
                    console.log(name)
                    updateChart(name)
                }};
                setInterval(updateChartName, 30000);
            }};
            names.forEach(setUpdateInterval);

        }};
    </script>
</html>
"""

def get_chart_page(names: list, creds: str, chart_type: str):
    chart_body = get_chart_body(names, creds, chart_type=chart_type)
    return f"""
<html>
    <head>
        
    </head>
    <body>
        {chart_body}
    </body>
</html>
"""