export class Dashboard extends HTMLElement {

    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
    }

    static observedAttributes = ["url", "stylesheet"];



    connectedCallback() {
        console.log("Dashboard added to the page.");
        const wsURL = this._url + "dashboard/statistics";
        const sock = SocketManager.getInstance(wsURL, "dashboard");

        // Create shadow DOM root
        const shadow = this.attachShadow({mode: "open"});
        let active = 0;
        this._shadow = shadow;

        // Apply external styles to the shadow dom
        const linkElem = document.createElement("link");
        linkElem.setAttribute("rel", "stylesheet");
        linkElem.setAttribute("href", this._styleUrl);
        shadow.appendChild(linkElem);

        const dashboardContainer = document.createElement("div");
        dashboardContainer.className = "columns"
        shadow.appendChild(dashboardContainer)

        const createColumn = () => {
            const col = document.createElement("div");
            col.className = "column";
            dashboardContainer.appendChild(col);
            return col;
        };

        const leftColumn = createColumn();
        const middleColumn = createColumn();
        const rightColumn = createColumn();

        // Build out the left column (Upload Number, Submission Graph, Location Graph)
        const uploadNumber = document.createElement("div");
        uploadNumber.style.height = "15vh";
        leftColumn.appendChild(uploadNumber)

        const submissionGraph = document.createElement("div");
        leftColumn.appendChild(submissionGraph)

        const locationGraph = document.createElement("div");
        leftColumn.appendChild(locationGraph)

        // Build out the middle column (Converted, Validated, and Submitted gauges)

        const convertedGauge = document.createElement("div");
        middleColumn.appendChild(convertedGauge);

        const validatedGauge = document.createElement("div");
        middleColumn.appendChild(validatedGauge);

        const submittedGauge = document.createElement("div");
        middleColumn.appendChild(submittedGauge)

        // Build out the right column (WIBL files container and Observers container)

        // Wibl Files Container
        const wiblFilesContainer = document.createElement("div");
        wiblFilesContainer.className = "block is-outlined";
        rightColumn.appendChild(wiblFilesContainer);

        const totalSizeNumber = document.createElement("div");
        wiblFilesContainer.appendChild(totalSizeNumber);

        const totalObservationsNumber = document.createElement("div");
        wiblFilesContainer.appendChild(totalObservationsNumber);

        const observersUsedGauge = document.createElement("div");
        wiblFilesContainer.appendChild(observersUsedGauge);

        // Observers Container
        const observersContainer = document.createElement("div");
        observersContainer.className = "block is-outlined";
        rightColumn.appendChild(observersContainer);

        const observerColumns = document.createElement("div");
        observerColumns.className = "columns";
        observersContainer.appendChild(observerColumns);

        const numbersColumn = document.createElement("div");
        numbersColumn.className = "column";
        observerColumns.appendChild(numbersColumn);

        const graphColumn = document.createElement("div");
        graphColumn.className = "column";
        observerColumns.appendChild(graphColumn);

        const totalObserversNumber = document.createElement("div");
        numbersColumn.appendChild(totalObserversNumber);

        const noReportsNumber = document.createElement("div");
        numbersColumn.appendChild(noReportsNumber);

        const observerFileCountGraph = document.createElement("div");
        graphColumn.appendChild(observerFileCountGraph);

        const observerSndCountGraph = document.createElement("div");
        graphColumn.appendChild(observerSndCountGraph);

        function scaleFont(baseSize, container) {
            const width = container.clientWidth || 400;
            return Math.max(10, baseSize * (width / 400));
        }

        function createGauge(elm, value, title, suffix="%") {
            Plotly.newPlot(elm, [{
                type: "indicator",
                mode: "gauge+number",
                value: value,
                title: { text: title , font: {size: scaleFont(16, elm)}},
                number: { suffix: suffix },
                domain: { x: [0, 1], y: [0, 1] },
                gauge: { axis: { range: [0, 100], tick0: 0, dtick: 20 } }
            }], {
                margin: { t: 40, b: 40, l: 40, r: 20 },
                height: 250,
                responsive: true,
                autosize: true
            });
        }


        function createNumber(elm, value, title, suffix="", numberFormat="") {
            Plotly.newPlot(elm, [{
                type: "indicator",
                mode: "number",
                value: value,
                title: { text: title, font: {size: scaleFont(16, elm)}},
                number: { valueFormat: numberFormat, suffix: suffix},
                domain: { x: [0, 1], y: [0, 1] }
            }], { margin: { t: 40, b: 40, l: 40, r: 20 },
                height: 250,
                responsive: true,
                autosize: true
            });
        }

        function createDashboard(message) {
            console.log("In loadData for Dashboard")
            const data = message.message;
            console.log(data["WIBLFileCount"]);
            createNumber(uploadNumber, data["WIBLFileCount"], "Uploaded");
//            Plotly.newPlot(uploadNumber, [
//                {
//                    type: "indicator",
//                    mode:"number",
//                    value:data["WIBLFileCount"],
//                    title:{'text': 'Uploaded'},
//                    domain:{'x': [0, 1], 'y': [0, 1]},
//                    number:{'valueformat': '.0f'}
//                }
//            ]);

            var submissionData = data["FileDateTotal"];
            console.log(submissionData);
            Plotly.newPlot(submissionGraph, [
                {
                    x: [1, 2, 3, 4],
                    y: [5, 6, 7, 8],
                    mode: "lines",
                    connectgaps: true
                }
            ]);

            Plotly.newPlot(locationGraph, [{
              type: 'scattergeo',
              mode: 'markers',
              lon: [],
              lat: [],
              marker: {
                size: 4,
                color: 'blue'
              }
            }], [{
               geo: {
                projection: {
                  type: 'natural earth'
                }
              }
            }]);

            createGauge(convertedGauge, (data["ConvertedTotal"] / data["WIBLFileCount"]) * 100, "Converted");

//            Plotly.newPlot(convertedGauge, [{
//                type: "indicator",
//                mode:"gauge+number",
//                value:(data["ConvertedTotal"] / data["WIBLFileCount"]) * 100,
//                number:{'suffix': '%'},
//                domain:{'x': [0, 1], 'y': [0, 1]},
//                gauge:{'axis': {'range': [0, 100], 'tick0': 0, 'dtick': 20}}
//            }]);

            createGauge(validatedGauge, (data["ValidatedTotal"] / data["GeoJSONFileCount"]) * 100, "Validated");
//            Plotly.newPlot(validatedGauge, [{
//                type: "indicator",
//                mode:'gauge+number',
//                value:(data["ValidatedTotal"] / data["GeoJSONFileCount"]) * 100,
//                title:{'text': 'Validated'},
//                number:{'suffix': '%'},
//                domain:{'x': [0, 1], 'y': [0, 1]},
//                gauge:{'axis': {'range': [0, 100], 'tick0': 0, 'dtick': 20}}
//            }]);

            createGauge(submittedGauge, (data["SubmittedTotal"] / data["GeoJSONFileCount"]) * 100, "Submitted");
//            Plotly.newPlot(submittedGauge, [{
//                type: "indicator",
//                mode:'gauge+number',
//                value:(data["SubmittedTotal"] / data["GeoJSONFileCount"]) * 100,
//                title:{'text': 'Submitted'},
//                number:{'suffix': '%'},
//                domain:{'x': [0, 1], 'y': [0, 1]},
//                gauge:{'axis': {'range': [0, 100], 'tick0': 0, 'dtick': 20}}
//            }]);
            createNumber(totalSizeNumber, data["SizeTotal"], "Total Size", "GB", ".2f");
//            Plotly.newPlot(totalSizeNumber, [{
//                type: "indicator",
//                mode:'number',
//                value: data["SizeTotal"],
//                title:{'text': 'Total Size'},
//                number:{'valueformat': '.2f', 'suffix': 'GB'},
//                domain:{'x': [0, 1], 'y': [0, 1]}
//            }]);

            createNumber(totalObservationsNumber, data["ObservationsTotal"], "M", ".2f");
//            Plotly.newPlot(totalObservationsNumber, [{
//                type: "indicator",
//                mode:'number',
//                value:data["ObservationsTotal"],
//                title:{'text': 'Total Observations'},
//                number:{'valueformat': '.2f', 'suffix': 'M'},
//                domain:{'x': [0, 1], 'y': [0, 1]}
//            }]);

            createGauge(observersUsedGauge, 0, "Observations Used");
//            Plotly.newPlot(observersUsedGauge, [{
//                type: "indicator",
//                mode:'gauge+number',
//                value:0,
//                title:{'text': 'Observations Used'},
//                number:{'suffix': '%'},
//                domain:{'x': [0, 1], 'y': [0, 1]},
//                gauge:{'axis': {'range': [0, 100], 'tick0': 0, 'dtick': 20}}
//            }]);

            createNumber(totalObservationsNumber, data["ObserverTotal"], "Total Observers");
//            Plotly.newPlot(totalObserversNumber, [{
//                type: "indicator",
//                mode:'number',
//                value:data["ObserverTotal"],
//                title:{'text': 'Total Observers'},
//                number:{'valueformat': '.0f'},
//                domain:{'x': [0, 1], 'y': [0, 1]}
//            }]);

            createNumber(noReportsNumber, data["ObserverZeroReportsTotal"], "Zero Reports/Last Month", "", ".0f")
//            Plotly.newPlot(noReportsNumber, [{
//                type: "indicator",
//                mode:'number',
//                value:data["ObserverZeroReportsTotal"],
//                title:{'text': 'Zero Reports/Last Month'},
//                number:{'valueformat': '.0f'},
//                domain:{'x': [0, 1], 'y': [0, 1]}
//            }]);

            Plotly.newPlot(observerFileCountGraph, [{
                 type: 'scatter',
                  mode: 'lines+markers',
                  x: [],
                  y: [],
                  line: { shape: 'linear' },
                  marker: { color: 'blue' }
            }]);

            Plotly.newPlot(observerSndCountGraph, [{
                 type: 'scatter',
                  mode: 'lines+markers',
                  x: [],
                  y: [],
                  line: { shape: 'linear' },
                  marker: { color: 'blue' }
            }]);
        }

        sock.addHandler("list-dashboard-statistics", createDashboard);
    }

    disconnectedCallback() {
        console.log("Dashboard removed from page.");
    }

    adoptedCallback() {
        console.log("Dashboard moved to a new page.");
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`Dashboard: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
        switch (name) {
            case "url":
                this._url = newValue;
                break;
            case "stylesheet":
                this._styleUrl = newValue;
                break;
            default:
                console.warn(`Unknown attribute ${name}`);
        }
    }
}

customElements.define("wibl-dashboard", Dashboard);